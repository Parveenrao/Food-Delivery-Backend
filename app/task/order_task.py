from celery import current_app
from sqlalchemy.orm  import Session
from app.database  import SessionLocal
from datetime import datetime , timedelta
from app.task.celery_app import celery_app
from app.models.order import Order , OrderStatus
from app.utils.websocket_manager import manager
from app.core.logging import logger

@celery_app.task
def update_order_status(order_id :int , new_status : str):
    # Update order and notify relevant parties 
    
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.error(f"Order not found" , order_id = order_id)
            return False
        
        
        old_status = order.status
        
        order.status = OrderStatus[new_status]
        
        #Update timestamp based on status 
        
        now = datetime.now()
        
        if new_status == OrderStatus.PREPARING.values:
            order.prepared_at = now
            
        elif new_status == OrderStatus.OUT_FOR_DELIVERY.value:
            order.picked_up_at = now
            
        elif new_status == OrderStatus.DELIVERED.value:
            order.delivered_at = now
            
        elif new_status == OrderStatus.CANCELLED.value:
            order.cancelled_at = now        
            
        db.commit()
        
        # Send real - time notifications 
        
        notification_message = {
            "type" : "order_status_update",
            "order_id" : order_id,
            "order_number" : Order.order_number,
            "old_status": old_status.value,
            "new_status": new_status,
            "timestamp": now.isoformat()
        }  
        
        # Notify customer 
        
        current_app.send_task(
            "app.tasks.notification_tasks.send_websocket_notification",
            args=[order.restaurant.owner_id, notification_message]
        )
        
        
        current_app.send_task(
            "app.tasks.notification_tasks.send_websocket_notification",
            args=[order.restaurant.owner_id, notification_message]
        )
        
        logger.info(f"Order status updated", order_id=order_id, 
                   old_status=old_status.value, new_status=new_status)
        return True
    
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update order status", order_id=order_id, error=str(e))
        return False
    finally:
        db.close()
        
@celery_app.task
def calculate_estimated_delivery_time(order_id :int):
    # Calculate and update estimate delivery time 
    
    db = SessionLocal()
    
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            return False
        
        # prep time 
        prep_time = order.restaurant.delivery_time or 30
        
        travel_time = 15  # Default 15 minutes
        
        estimated_time = datetime.now() + timedelta(minutes=prep_time + travel_time)
        
        order.estimated_delivery_time = estimated_time
        db.commit()
        
        # Notify customer about delivery time
        notification = {
            "type": "delivery_time_update",
            "order_id": order.id,
            "estimated_delivery_time": estimated_time.isoformat()
        }

        current_app.send_task(
            "app.tasks.notification_tasks.send_websocket_notification",
            args=[order.customer_id, notification]
        )
        
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to calculate delivery time", order_id=order_id, error=str(e))
        return False
    finally:
        db.close()


@celery_app.task
def auto_cancel_unpaid_order():
    db = SessionLocal()
    
    try:
        cutoff_time = datetime.now() + timedelta(minutes=15)
        
        unpaid_orders = db.query(Order).filter(Order.status == OrderStatus , Order.created_at < cutoff_time).all()
        
        cancelled_count = 0
        
        
        for order in unpaid_orders:
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = datetime.now()
            cancelled_count +=1
            
         # Notify customer
            notification = {
                "type": "order_cancelled",
                "order_id": order.id,
                "reason": "Payment timeout",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            current_app.send_task(
                "app.tasks.notification_tasks.send_websocket_notification",
                args=[order.customer_id, notification]
            )
        
        db.commit()
        logger.info(f"Auto-cancelled {cancelled_count} unpaid orders")
        return cancelled_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to cancel unpaid orders", error=str(e))
        return 0
    finally:
        db.close()    
        
        


    
            