from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from datetime import datetime
from app.models.order import Order, OrderItem, OrderStatus
from app.models.restaurant import Restaurant, MenuItem
from app.models.user import User
from app.core.exception import ValidationException, NotFoundException, AuthorizationException
from app.core.logging import logger
from app.utils.helpers import (
    calculate_distance, 
    calculate_delivery_fee, 
    calculate_order_total,
    generate_order_number
)


class OrderService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_order(
        self, 
        customer_id: int, 
        restaurant_id: int, 
        items: List[Dict], 
        delivery_address: str,
        delivery_latitude: Optional[float] = None,
        delivery_longitude: Optional[float] = None,
        delivery_instructions: Optional[str] = None
    ) -> Order:
        
        
    
        restaurant = self.db.query(Restaurant).filter(
            Restaurant.id == restaurant_id,
            Restaurant.is_active == True
        ).first()
        
        if not restaurant:
            raise NotFoundException("Restaurant")
        
        
        subtotal = 0
        order_items_data = []
        
        for item in items:
            menu_item = self.db.query(MenuItem).filter(
                MenuItem.id == item['menu_item_id'],
                MenuItem.restaurant_id == restaurant_id,
                MenuItem.is_available == True
            ).first()
            
            if not menu_item:
                raise ValidationException(f"Menu item {item['menu_item_id']} not available")
            
            if item['quantity'] <= 0:
                raise ValidationException("Quantity must be greater than 0")
            
            item_total = menu_item.price * item['quantity']
            subtotal += item_total
            
            order_items_data.append({
                'menu_item_id': item['menu_item_id'],
                'quantity': item['quantity'],
                'unit_price': menu_item.price,
                'total_price': item_total,
                'special_instructions': item.get('special_instructions')
            })
        
        
        if subtotal < restaurant.minimum_order:
            raise ValidationException(
                f"Minimum order amount is ${restaurant.minimum_order:.2f}"
            )
        
        
        delivery_fee = restaurant.delivery_fee
        if delivery_latitude and delivery_longitude and restaurant.latitude and restaurant.longitude:
            distance = calculate_distance(
                restaurant.latitude, restaurant.longitude,
                delivery_latitude, delivery_longitude
            )
            delivery_fee = calculate_delivery_fee(distance, base_fee=restaurant.delivery_fee)
        
        
        totals = calculate_order_total(
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            tax_rate=0.08,
            discount_amount=0.0
        )
        
        order = Order(
            order_number=generate_order_number(),
            customer_id=customer_id,
            restaurant_id=restaurant_id,
            subtotal=totals['subtotal'],
            delivery_fee=totals['delivery_fee'],
            tax_amount=totals['tax_amount'],
            discount_amount=totals['discount_amount'],
            total_amount=totals['total_amount'],
            delivery_address=delivery_address,
            delivery_latitude=delivery_latitude,
            delivery_longitude=delivery_longitude,
            delivery_instructions=delivery_instructions
        )
        
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        
        
        for item_data in order_items_data:
            order_item = OrderItem(order_id=order.id, **item_data)
            self.db.add(order_item)
        
        self.db.commit()
        
        logger.info(f"Order created", order_id=order.id, customer_id=customer_id)
        
        return order
    
    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID"""
        return self.db.query(Order).filter(Order.id == order_id).first()
    
    def get_order_by_number(self, order_number: str) -> Optional[Order]:
        """Get order by order number"""
        return self.db.query(Order).filter(Order.order_number == order_number).first()
    
    def get_user_orders(
        self, 
        user_id: int, 
        status: Optional[OrderStatus] = None,
        limit: int = 20
    ) -> List[Order]:
        
        
        query = self.db.query(Order).filter(Order.customer_id == user_id)
        
        if status:
            query = query.filter(Order.status == status)
        
        return query.order_by(Order.created_at.desc()).limit(limit).all()
    
    def get_restaurant_orders(
        self, 
        restaurant_id: int, 
        status: Optional[OrderStatus] = None,
        limit: int = 50
    ) -> List[Order]:
        
        
        query = self.db.query(Order).filter(Order.restaurant_id == restaurant_id)
        
        if status:
            query = query.filter(Order.status == status)
        
        return query.order_by(Order.created_at.desc()).limit(limit).all()
    
    def update_order_status(
        self, 
        order_id: int, 
        new_status: OrderStatus,
        updated_by_id: int
    ) -> Order:
        
        
        order = self.get_order_by_id(order_id)
        if not order:
            raise NotFoundException("Order")
        
        
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
            OrderStatus.PREPARING: [OrderStatus.READY_FOR_PICKUP, OrderStatus.CANCELLED],
            OrderStatus.READY_FOR_PICKUP: [OrderStatus.OUT_FOR_DELIVERY],
            OrderStatus.OUT_FOR_DELIVERY: [OrderStatus.DELIVERED],
        }
        
        if order.status in valid_transitions:
            if new_status not in valid_transitions[order.status]:
                raise ValidationException(
                    f"Cannot transition from {order.status.value} to {new_status.value}"
                )
        
        old_status = order.status
        order.status = new_status
        
        
        now = datetime.utcnow()
        if new_status == OrderStatus.PREPARING:
            order.prepared_at = now
        elif new_status == OrderStatus.OUT_FOR_DELIVERY:
            order.picked_up_at = now
        elif new_status == OrderStatus.DELIVERED:
            order.delivered_at = now
        elif new_status == OrderStatus.CANCELLED:
            order.cancelled_at = now
        
        self.db.commit()
        self.db.refresh(order)
        
        logger.info(
            f"Order status updated",
            order_id=order_id,
            old_status=old_status.value,
            new_status=new_status.value,
            updated_by=updated_by_id
        )
        
        return order
    
    def assign_delivery_partner(self, order_id: int, delivery_partner_id: int) -> Order:
        
        
        order = self.get_order_by_id(order_id)
        if not order:
            raise NotFoundException("Order")
        
        if order.status != OrderStatus.READY_FOR_PICKUP:
            raise ValidationException("Order not ready for pickup")
        
        order.delivery_partner_id = delivery_partner_id
        self.db.commit()
        self.db.refresh(order)
        
        logger.info(
            f"Delivery partner assigned",
            order_id=order_id,
            delivery_partner_id=delivery_partner_id
        )
        
        return order
    
    def cancel_order(self, order_id: int, user_id: int, reason: Optional[str] = None) -> Order:
        
        
        order = self.get_order_by_id(order_id)
        if not order:
            raise NotFoundException("Order")
        
        
        if order.customer_id != user_id:
            raise AuthorizationException("Not authorized to cancel this order")
        
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
            raise ValidationException("Order cannot be cancelled at this stage")
        
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(order)
        
        logger.info(f"Order cancelled", order_id=order_id, reason=reason)
        
        return order

