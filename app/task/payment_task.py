from celery import current_app
from sqlalchemy.orm import Session
from app.task.celery_app import celery_app
from app.database import SessionLocal
from app.models.payment import Payment, PaymentStatus
from app.models.order import Order, OrderStatus
from app.service.payment_service import PaymentService
from app.core.logging import logger
from datetime import datetime, timedelta

@celery_app.task
def process_payment(payment_id: int):

    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            logger.error(f"Payment not found", payment_id=payment_id)
            return False
        
        payment_service = PaymentService(db)
        success = payment_service.process_stripe_payment(payment)
        
        if success:
            # Update order status
            order = db.query(Order).filter(Order.id == payment.order_id).first()
            if order:
                current_app.send_task(
                    
                    args=[order.id, OrderStatus.CONFIRMED.value]
                )
                
                # Calculate estimated delivery time
                current_app.send_task(
                    
                    args=[order.id]
                )
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to process payment", payment_id=payment_id, error=str(e))
        return False
    finally:
        db.close()

@celery_app.task
def check_pending_payments():
    
    db = SessionLocal()
    try:
        # Check payments that are older than 5 minutes
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        
        pending_payments = db.query(Payment).filter(
            Payment.status == PaymentStatus.PENDING,
            Payment.created_at < cutoff_time
        ).all()
        
        payment_service = PaymentService(db)
        updated_count = 0
        
        for payment in pending_payments:
            if payment.stripe_payment_intent_id:
                status = payment_service.check_stripe_payment_status(
                    payment.stripe_payment_intent_id
                )
                if status != payment.status:
                    payment.status = status
                    updated_count += 1
                    
                    
                    if status == PaymentStatus.COMPLETED:
                        current_app.send_task(
                            "app.tasks.order_tasks.update_order_status",
                            args=[payment.order_id, OrderStatus.CONFIRMED.value]
                        )
                    elif status == PaymentStatus.FAILED:
                        current_app.send_task(
                            "app.tasks.order_tasks.update_order_status",
                            args=[payment.order_id, OrderStatus.CANCELLED.value]
                        )
        
        db.commit()
        logger.info(f"Updated {updated_count} payment statuses")
        return updated_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to check pending payments", error=str(e))
        return 0
    finally:
        db.close()

@celery_app.task
def process_refund(payment_id: int, refund_amount: float = None):
    
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            logger.error(f"Payment not found for refund", payment_id=payment_id)
            return False
        
        payment_service = PaymentService(db)
        success = payment_service.process_refund(payment, refund_amount)
        
        if success:
            # Update order status
            current_app.send_task(
                "app.tasks.order_tasks.update_order_status",
                args=[payment.order_id, OrderStatus.REFUNDED.value]
            )
            
            # Notify customer
            notification = {
                "type": "refund_processed",
                "order_id": payment.order_id,
                "refund_amount": refund_amount or payment.amount,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            current_app.send_task(
                "app.tasks.notification_tasks.send_websocket_notification",
                args=[payment.user_id, notification]
            )
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to process refund", payment_id=payment_id, error=str(e))
        return False
    finally:
        db.close()