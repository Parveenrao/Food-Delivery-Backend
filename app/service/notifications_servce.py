from typing import Dict, Any, Optional
from app.core.logging import logger
from app.task.notification_task import (
    send_email_notification,
    send_sms_notification,
    send_push_notification,
    send_websocket_notification
)


class NotificationService:
    
    @staticmethod
    def send_order_notification(
        order_id: int,
        user_id: int,
        notification_type: str,
        data: Dict[str, Any]
    ):
        """Send order-related notification"""
        
        notification_message = {
            'type': notification_type,
            'order_id': order_id,
            **data
        }
        
        # Send via WebSocket for real-time update
        send_websocket_notification.delay(user_id, notification_message)
        
        logger.info(
            f"Order notification sent",
            order_id=order_id,
            user_id=user_id,
            type=notification_type
        )
    
    @staticmethod
    def send_order_status_update(
        order_id: int,
        customer_id: int,
        restaurant_owner_id: int,
        delivery_partner_id: Optional[int],
        old_status: str,
        new_status: str
    ):
        """Send order status update to all relevant parties"""
        
        notification_data = {
            'order_id': order_id,
            'old_status': old_status,
            'new_status': new_status
        }
        
        # Notify customer
        NotificationService.send_order_notification(
            order_id, customer_id, 'order_status_update', notification_data
        )
        
        # Notify restaurant
        NotificationService.send_order_notification(
            order_id, restaurant_owner_id, 'order_status_update', notification_data
        )
        
        # Notify delivery partner if assigned
        if delivery_partner_id:
            NotificationService.send_order_notification(
                order_id, delivery_partner_id, 'order_status_update', notification_data
            )
    
    @staticmethod
    def send_payment_notification(
        user_id: int,
        payment_status: str,
        amount: float,
        order_id: int
    ):
        """Send payment notification"""
        
        notification_data = {
            'type': 'payment_update',
            'status': payment_status,
            'amount': amount,
            'order_id': order_id
        }
        
        send_websocket_notification.delay(user_id, notification_data)
        
        logger.info(
            f"Payment notification sent",
            user_id=user_id,
            status=payment_status
        )