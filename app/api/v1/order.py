from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.database import get_db
from app.api.deps import get_current_user, get_restaurant_owner, get_delivery_partner
from app.models.user import User
from app.models.order import Order, OrderItem, OrderStatus
from app.models.restaurant import Restaurant, MenuItem
from app.schema.order import OrderCreate, OrderResponse, OrderUpdate
from app.core.exception import NotFoundException, ValidationException, AuthorizationException
from app.task.order_task import update_order_status, calculate_estimated_delivery_time
from app.core.logging import logger

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    '''Create a new order'''
    
    # Verify restaurant exists and is active
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == order_data.restaurant_id,
        Restaurant.is_active == True
    ).first()
    
    if not restaurant:
        raise NotFoundException("Restaurant")
    
    # Calculate order totals
    subtotal = 0
    order_items_data = []
    
    for item in order_data.items:
        menu_item = db.query(MenuItem).filter(
            MenuItem.id == item.menu_item_id,
            MenuItem.restaurant_id == order_data.restaurant_id,
            MenuItem.is_available == True
        ).first()
        
        if not menu_item:
            raise ValidationException(f"Menu item {item.menu_item_id} not available")
        
        if item.quantity <= 0:
            raise ValidationException("Quantity must be greater than 0")
        
        item_total = menu_item.price * item.quantity
        subtotal += item_total
        
        order_items_data.append({
            "menu_item_id": item.menu_item_id,
            "quantity": item.quantity,
            "unit_price": menu_item.price,
            "total_price": item_total,
            "special_instructions": item.special_instructions
        })
    
    # Calculate fees and taxes
    delivery_fee = restaurant.delivery_fee
    tax_rate = 0.08  # 8% tax
    tax_amount = subtotal * tax_rate
    total_amount = subtotal + delivery_fee + tax_amount
    
    # Check minimum order requirement
    if subtotal < restaurant.minimum_order:
        raise ValidationException(
            f"Minimum order amount is ${restaurant.minimum_order:.2f}"
        )
    
    # Create order
    db_order = Order(
        customer_id=current_user.id,
        restaurant_id=order_data.restaurant_id,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        tax_amount=tax_amount,
        total_amount=total_amount,
        delivery_address=order_data.delivery_address,
        delivery_latitude=order_data.delivery_latitude,
        delivery_longitude=order_data.delivery_longitude,
        delivery_instructions=order_data.delivery_instructions
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Create order items
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=db_order.id,
            **item_data
        )
        db.add(order_item)
    
    db.commit()
    
    # Calculate estimated delivery time
    calculate_estimated_delivery_time.delay(db_order.id)
    
    # Load order with items for response
    order_with_items = db.query(Order).options(
        joinedload(Order.items)
    ).filter(Order.id == db_order.id).first()
    
    logger.info(f"Order created", order_id=db_order.id, customer_id=current_user.id)
    
    return order_with_items

@router.get("/", response_model=List[OrderResponse])
async def get_my_orders(
    status: Optional[OrderStatus] = Query(None, description="Filter by order status"),
    limit: int = Query(20, le=100, description="Number of orders to return"),
    offset: int = Query(0, description="Number of orders to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    '''Get current user's orders'''
    
    query = db.query(Order).options(
        joinedload(Order.items)
    ).filter(Order.customer_id == current_user.id)
    
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    
    return orders

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    '''Get order details'''
    
    order = db.query(Order).options(
        joinedload(Order.items)
    ).filter(Order.id == order_id).first()
    
    if not order:
        raise NotFoundException("Order")
    
    # Check if user has permission to view this order
    if (order.customer_id != current_user.id and
        order.delivery_partner_id != current_user.id and
        current_user.role.value != "admin"):
        
        # Check if user is restaurant owner
        restaurant = db.query(Restaurant).filter(
            Restaurant.id == order.restaurant_id,
            Restaurant.owner_id == current_user.id
        ).first()
        
        if not restaurant:
            raise AuthorizationException("Access denied to this order")
    
    return order

@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_update: OrderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    '''Update order status'''
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Order")
    
    # Check permissions based on user role and status change
    if order_update.status:
        new_status = order_update.status
        
        # Restaurant owner can update to preparing, ready_for_pickup
        if (current_user.role.value == "restaurant_owner" and 
            new_status in [OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY_FOR_PICKUP]):
            
            restaurant = db.query(Restaurant).filter(
                Restaurant.id == order.restaurant_id,
                Restaurant.owner_id == current_user.id
            ).first()
            
            if not restaurant:
                raise AuthorizationException("Not authorized to update this order")
        
        # Delivery partner can update to out_for_delivery, delivered
        elif (current_user.role.value == "delivery_partner" and 
              new_status in [OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED]):
            
            if order.delivery_partner_id != current_user.id:
                raise AuthorizationException("Not assigned to this order")
        
        # Customer can only cancel pending orders
        elif (current_user.role.value == "customer" and 
              new_status == OrderStatus.CANCELLED):
            
            if (order.customer_id != current_user.id or 
                order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]):
                raise AuthorizationException("Cannot cancel this order")
        
        # Admin can update any status
        elif current_user.role.value != "admin":
            raise AuthorizationException("Not authorized to update order status")
        
        # Trigger async status update
        update_order_status.delay(order_id, new_status.value)
    
    # Update delivery partner assignment
    if order_update.delivery_partner_id is not None:
        if current_user.role.value not in ["admin", "restaurant_owner"]:
            raise AuthorizationException("Not authorized to assign delivery partner")
        
        order.delivery_partner_id = order_update.delivery_partner_id
        db.commit()
    
    db.refresh(order)
    return order

@router.get("/restaurant/{restaurant_id}", response_model=List[OrderResponse])
async def get_restaurant_orders(
    restaurant_id: int,
    status: Optional[OrderStatus] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    current_user: User = Depends(get_restaurant_owner),
    db: Session = Depends(get_db)
):
    '''Get orders for a restaurant (restaurant owner only)'''
    
    # Verify restaurant ownership
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.owner_id == current_user.id
    ).first()
    
    if not restaurant:
        raise NotFoundException("Restaurant or access denied")
    
    query = db.query(Order).options(
        joinedload(Order.items)
    ).filter(Order.restaurant_id == restaurant_id)
    
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    
    return orders

@router.get("/delivery/available", response_model=List[OrderResponse])
async def get_available_deliveries(
    limit: int = Query(20, le=50),
    current_user: User = Depends(get_delivery_partner),
    db: Session = Depends(get_db)
):
    '''Get available delivery orders (delivery partner only)'''
    
    # Get orders that are ready for pickup and don't have a delivery partner
    orders = db.query(Order).options(
        joinedload(Order.items)
    ).filter(
        Order.status == OrderStatus.READY_FOR_PICKUP,
        Order.delivery_partner_id.is_(None)
    ).order_by(Order.created_at.asc()).limit(limit).all()
    
    return orders

@router.patch("/delivery/{order_id}/accept")
async def accept_delivery(
    order_id: int,
    current_user: User = Depends(get_delivery_partner),
    db: Session = Depends(get_db)
):
    '''Accept a delivery order (delivery partner only)'''
    
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.status == OrderStatus.READY_FOR_PICKUP,
        Order.delivery_partner_id.is_(None)
    ).first()
    
    if not order:
        raise NotFoundException("Available delivery order")
    
    # Assign delivery partner
    order.delivery_partner_id = current_user.id
    db.commit()
    
    logger.info(f"Delivery accepted", order_id=order_id, delivery_partner_id=current_user.id)
    
    return {"message": "Delivery accepted successfully"}