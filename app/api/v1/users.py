from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserAddress
from app.schema.user import UserResponse, UserUpdate, AddressCreate, AddressResponse
from app.core.exception import NotFoundException, ValidationException
from app.core.logging import logger
from app.task.user_task import sync_user_preferences

router = APIRouter(prefix="/users", tags=["users"])


# ==================== User Profile Endpoints ====================

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Update user fields
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    # Sync preferences to cache
    sync_user_preferences.delay(current_user.id)
    
    logger.info(f"User profile updated", user_id=current_user.id)
    
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user account (soft delete)"""
    
    # Soft delete - just deactivate
    current_user.is_active = False
    db.commit()
    
    # Send confirmation email
    from app.task.user_task import send_account_deletion_confirmation
    send_account_deletion_confirmation.delay(current_user.id)
    
    logger.info(f"User account deleted", user_id=current_user.id)
    
    return None


# ==================== Address Management Endpoints ====================

@router.post("/addresses", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
async def create_address(
    address_data: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add new address for current user"""
    
    # If this is default address, unset other default addresses
    if address_data.is_default:
        db.query(UserAddress).filter(
            UserAddress.user_id == current_user.id,
            UserAddress.is_default == True
        ).update({"is_default": False})
    
    # Create new address
    db_address = UserAddress(
        user_id=current_user.id,
        title=address_data.title,
        address_line_1=address_data.address_line_1,
        address_line_2=address_data.address_line_2,
        city=address_data.city,
        state=address_data.state,
        postal_code=address_data.postal_code,
        latitude=address_data.latitude,
        longitude=address_data.longitude,
        is_default=address_data.is_default
    )
    
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    
    # Sync updated preferences
    sync_user_preferences.delay(current_user.id)
    
    logger.info(f"Address created", address_id=db_address.id, user_id=current_user.id)
    
    return db_address


@router.get("/addresses", response_model=List[AddressResponse])
async def get_user_addresses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all addresses for current user"""
    
    addresses = db.query(UserAddress).filter(
        UserAddress.user_id == current_user.id
    ).order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc()).all()
    
    return addresses


@router.get("/addresses/{address_id}", response_model=AddressResponse)
async def get_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific address"""
    
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == current_user.id
    ).first()
    
    if not address:
        raise NotFoundException("Address")
    
    return address


@router.patch("/addresses/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: int,
    address_update: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update address"""
    
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == current_user.id
    ).first()
    
    if not address:
        raise NotFoundException("Address")
    
    # If setting as default, unset other default addresses
    if address_update.is_default and not address.is_default:
        db.query(UserAddress).filter(
            UserAddress.user_id == current_user.id,
            UserAddress.is_default == True,
            UserAddress.id != address_id
        ).update({"is_default": False})
    
    # Update address fields
    update_data = address_update.model_dump()
    for field, value in update_data.items():
        setattr(address, field, value)
    
    db.commit()
    db.refresh(address)
    
    # Sync updated preferences
    sync_user_preferences.delay(current_user.id)
    
    logger.info(f"Address updated", address_id=address_id, user_id=current_user.id)
    
    return address


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete address"""
    
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == current_user.id
    ).first()
    
    if not address:
        raise NotFoundException("Address")
    
    # Don't allow deleting the only address or default address without replacement
    address_count = db.query(UserAddress).filter(
        UserAddress.user_id == current_user.id
    ).count()
    
    if address_count == 1:
        raise ValidationException("Cannot delete your only address")
    
    if address.is_default:
        # Set another address as default before deleting
        other_address = db.query(UserAddress).filter(
            UserAddress.user_id == current_user.id,
            UserAddress.id != address_id
        ).first()
        
        if other_address:
            other_address.is_default = True
    
    db.delete(address)
    db.commit()
    
    # Sync updated preferences
    sync_user_preferences.delay(current_user.id)
    
    logger.info(f"Address deleted", address_id=address_id, user_id=current_user.id)
    
    return None


@router.patch("/addresses/{address_id}/set-default", response_model=AddressResponse)
async def set_default_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set an address as default"""
    
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == current_user.id
    ).first()
    
    if not address:
        raise NotFoundException("Address")
    
    # Unset all other default addresses
    db.query(UserAddress).filter(
        UserAddress.user_id == current_user.id,
        UserAddress.is_default == True
    ).update({"is_default": False})
    
    # Set this as default
    address.is_default = True
    db.commit()
    db.refresh(address)
    
    # Sync updated preferences
    sync_user_preferences.delay(current_user.id)
    
    logger.info(f"Default address updated", address_id=address_id, user_id=current_user.id)
    
    return address


# ==================== User Statistics Endpoints ====================

@router.get("/me/stats")
async def get_user_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user order statistics"""
    
    from app.models.order import Order, OrderStatus
    from sqlalchemy import func
    
    # Total orders
    total_orders = db.query(Order).filter(
        Order.customer_id == current_user.id
    ).count()
    
    # Total spent
    total_spent = db.query(func.sum(Order.total_amount)).filter(
        Order.customer_id == current_user.id,
        Order.status == OrderStatus.DELIVERED
    ).scalar() or 0
    
    # Orders in progress
    active_orders = db.query(Order).filter(
        Order.customer_id == current_user.id,
        Order.status.in_([
            OrderStatus.PENDING,
            OrderStatus.CONFIRMED,
            OrderStatus.PREPARING,
            OrderStatus.OUT_FOR_DELIVERY
        ])
    ).count()
    
    # Completed orders
    completed_orders = db.query(Order).filter(
        Order.customer_id == current_user.id,
        Order.status == OrderStatus.DELIVERED
    ).count()
    
    # Cancelled orders
    cancelled_orders = db.query(Order).filter(
        Order.customer_id == current_user.id,
        Order.status == OrderStatus.CANCELLED
    ).count()
    
    # Average order value
    avg_order_value = float(total_spent / completed_orders) if completed_orders > 0 else 0
    
    # Favorite restaurants
    favorite_restaurants = db.query(
        Order.restaurant_id,
        func.count(Order.id).label('order_count')
    ).filter(
        Order.customer_id == current_user.id,
        Order.status == OrderStatus.DELIVERED
    ).group_by(Order.restaurant_id).order_by(
        func.count(Order.id).desc()
    ).limit(5).all()
    
    return {
        "total_orders": total_orders,
        "total_spent": float(total_spent),
        "active_orders": active_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "average_order_value": round(avg_order_value, 2),
        "favorite_restaurants": [
            {
                "restaurant_id": r[0],
                "order_count": r[1]
            } for r in favorite_restaurants
        ]
    }


@router.get("/me/recent-activity")
async def get_recent_activity(
    limit: int = Query(10, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's recent activity"""
    
    from app.models.order import Order
    
    recent_orders = db.query(Order).filter(
        Order.customer_id == current_user.id
    ).order_by(Order.created_at.desc()).limit(limit).all()
    
    activities = []
    for order in recent_orders:
        activities.append({
            "type": "order",
            "order_id": order.id,
            "order_number": order.order_number,
            "status": order.status.value,
            "amount": float(order.total_amount),
            "created_at": order.created_at.isoformat()
        })
    
    return activities


# ==================== User Preferences Endpoints ====================

@router.get("/me/preferences")
async def get_user_preferences(
    current_user: User = Depends(get_current_user)
):
    """Get user preferences from cache"""
    
    from app.utils.redis_client import redis_client
    import asyncio
    
    # Try to get from cache
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    cached_prefs = loop.run_until_complete(
        redis_client.get(f"user_preferences:{current_user.id}")
    )
    loop.close()
    
    if cached_prefs:
        import json
        return json.loads(cached_prefs)
    
    # If not in cache, trigger sync and return basic info
    sync_user_preferences.delay(current_user.id)
    
    return {
        "user_id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role.value
    }