from celery import current_app
from app.task.celery_app import celery_app
from app.utils.websocket_manager import manager
from app.utils.redis_client import redis_client
from app.core.logging import logger
import asyncio

@celery_app.task
def send_websocket_notification(user_id: int, message: dict):
    
    try:
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(manager.send_personal_message(message, user_id))
        loop.close()
        
        logger.info(f"WebSocket notification sent", user_id=user_id, message_type=message.get('type'))
        return True
    except Exception as e:
        logger.error(f"Failed to send WebSocket notification", user_id=user_id, error=str(e))
        return False

@celery_app.task
def send_email_notification(user_email: str, subject: str, template: str, context: dict):
    try:
        
        
        logger.info(f"Email notification sent", email=user_email, subject=subject)
        return True
    except Exception as e:
        logger.error(f"Failed to send email notification", email=user_email, error=str(e))
        return False

@celery_app.task
def send_sms_notification(phone_number: str, message: str):
   
    try:
        
        
        logger.info(f"SMS notification sent", phone=phone_number)
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS notification", phone=phone_number, error=str(e))
        return False

@celery_app.task
def send_push_notification(user_id: int, title: str, body: str, data: dict = None):
    
    try:
        # Implement push notification logic here
        # Example: Firebase Cloud Messaging, OneSignal, etc.
        
        logger.info(f"Push notification sent", user_id=user_id, title=title)
        return True
    except Exception as e:
        logger.error(f"Failed to send push notification", user_id=user_id, error=str(e))
        return False

@celery_app.task
def broadcast_system_notification(message: dict, roles: list = None):
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if roles:
            for role in roles:
                loop.run_until_complete(manager.send_to_role(message, role))
        else:
            loop.run_until_complete(manager.broadcast(message))
        
        loop.close()
        
        logger.info(f"System notification broadcasted", roles=roles)
        return True
    except Exception as e:
        logger.error(f"Failed to broadcast system notification", error=str(e))
        return False