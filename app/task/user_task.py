# ================================================================
# FILE: app/tasks/user_tasks.py
# LOCATION: food_delivery_backend/app/tasks/user_tasks.py
# 
# User-related background tasks using Celery
# Handles email verification, password reset, activity tracking, etc.
# ================================================================

from celery import current_app
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.task.celery_app import celery_app
from app.database import SessionLocal
from app.models.user import User, UserAddress
from app.utils.redis_client import redis_client
from app.core.logging import logger
from app.utils.helpers import generate_otp, generate_verification_token
import asyncio


@celery_app.task
def send_welcome_email(user_id: int):
    '''Send welcome email to new user'''
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User not found for welcome email", user_id=user_id)
            return False
        
        # Send welcome email
        email_subject = "Welcome to Food Delivery!"
        email_body = f"""
        Hi {user.full_name},
        
        Welcome to our food delivery platform!
        
        Your account has been successfully created.
        Username: {user.username}
        Email: {user.email}
        
        Start ordering from your favorite restaurants now!
        
        Best regards,
        Food Delivery Team
        """
        
        # Trigger email notification task
        current_app.send_task(
            "app.tasks.notification_tasks.send_email_notification",
            args=[user.email, email_subject, "welcome_email", {"user": user.full_name}]
        )
        
        logger.info(f"Welcome email sent", user_id=user_id)
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email", user_id=user_id, error=str(e))
        return False
    finally:
        db.close()


@celery_app.task
def send_verification_email(user_id: int):
    '''Send email verification link to user'''
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User not found for verification", user_id=user_id)
            return False
        
        # Generate verification token
        token = generate_verification_token()
        
        # Store token in Redis with 24 hour expiration
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            redis_client.set(f"verify_email:{token}", user_id, expire=86400)
        )
        loop.close()
        
        # Generate verification URL
        verification_url = f"https://yourapp.com/verify-email?token={token}"
        
        # Send verification email
        email_subject = "Verify Your Email Address"
        email_body = f"""
        Hi {user.full_name},
        
        Please verify your email address by clicking the link below:
        
        {verification_url}
        
        This link will expire in 24 hours.
        
        If you didn't create this account, please ignore this email.
        
        Best regards,
        Food Delivery Team
        """
        
        current_app.send_task(
            "app.tasks.notification_tasks.send_email_notification",
            args=[user.email, email_subject, "verify_email", {
                "user": user.full_name,
                "verification_url": verification_url
            }]
        )
        
        logger.info(f"Verification email sent", user_id=user_id)
        return True
        
    except Exception as e:
        logger.error(f"Failed to send verification email", user_id=user_id, error=str(e))
        return False
    finally:
        db.close()


@celery_app.task
def send_password_reset_email(user_id: int):
    '''Send password reset link to user'''
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User not found for password reset", user_id=user_id)
            return False
        
        # Generate reset token
        token = generate_verification_token()
        
        # Store token in Redis with 1 hour expiration
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            redis_client.set(f"reset_password:{token}", user_id, expire=3600)
        )
        loop.close()
        
        # Generate reset URL
        reset_url = f"https://yourapp.com/reset-password?token={token}"
        
        # Send reset email
        email_subject = "Reset Your Password"
        email_body = f"""
        Hi {user.full_name},
        
        You requested to reset your password. Click the link below to create a new password:
        
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you didn't request this, please ignore this email and your password will remain unchanged.
        
        Best regards,
        Food Delivery Team
        """
        
        current_app.send_task(
            "app.tasks.notification_tasks.send_email_notification",
            args=[user.email, email_subject, "reset_password", {
                "user": user.full_name,
                "reset_url": reset_url
            }]
        )
        
        logger.info(f"Password reset email sent", user_id=user_id)
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email", user_id=user_id, error=str(e))
        return False
    finally:
        db.close()


@celery_app.task
def send_2fa_code(user_id: int):
    '''Send 2FA OTP code to user'''
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User not found for 2FA", user_id=user_id)
            return False
        
        # Generate OTP
        otp = generate_otp(length=6)
        
        # Store OTP in Redis with 5 minute expiration
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            redis_client.set(f"2fa_otp:{user_id}", otp, expire=300)
        )
        loop.close()
        
        # Send OTP via SMS
        if user.phone:
            message = f"Your verification code is: {otp}. Valid for 5 minutes."
            current_app.send_task(
                "app.tasks.notification_tasks.send_sms_notification",
                args=[user.phone, message]
            )
        
        # Also send via email as backup
        email_subject = "Your Verification Code"
        current_app.send_task(
            "app.tasks.notification_tasks.send_email_notification",
            args=[user.email, email_subject, "2fa_code", {
                "user": user.full_name,
                "otp": otp
            }]
        )
        
        logger.info(f"2FA code sent", user_id=user_id)
        return True
        
    except Exception as e:
        logger.error(f"Failed to send 2FA code", user_id=user_id, error=str(e))
        return False
    finally:
        db.close()


@celery_app.task
def update_user_activity(user_id: int, activity_type: str, metadata: dict = None):
    '''Track user activity'''
    try:
        activity_data = {
            'user_id': user_id,
            'activity_type': activity_type,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store in Redis for real-time tracking
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            redis_client.set(
                f"user_activity:{user_id}:latest",
                activity_data,
                expire=3600
            )
        )
        loop.close()
        
        logger.info(f"User activity tracked", user_id=user_id, activity=activity_type)
        return True
        
    except Exception as e:
        logger.error(f"Failed to track user activity", user_id=user_id, error=str(e))
        return False


@celery_app.task
def deactivate_inactive_users():
    '''Deactivate users who haven't logged in for 1 year'''
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        # Find inactive users (would need last_login field in production)
        inactive_users = db.query(User).filter(
            User.is_active == True,
            User.created_at < cutoff_date
        ).all()
        
        deactivated_count = 0
        for user in inactive_users:
            # Check if user has any orders in last year
            from app.models.order import Order
            recent_orders = db.query(Order).filter(
                Order.customer_id == user.id,
                Order.created_at > cutoff_date
            ).count()
            
            if recent_orders == 0:
                user.is_active = False
                deactivated_count += 1
                
                # Send notification
                current_app.send_task(
                    "app.tasks.notification_tasks.send_email_notification",
                    args=[user.email, "Account Deactivated", "account_deactivated", {
                        "user": user.full_name
                    }]
                )
        
        db.commit()
        logger.info(f"Deactivated {deactivated_count} inactive users")
        return deactivated_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to deactivate inactive users", error=str(e))
        return 0
    finally:
        db.close()


@celery_app.task
def sync_user_preferences(user_id: int):
    '''Sync user preferences to cache'''
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Get user's default address
        default_address = db.query(UserAddress).filter(
            UserAddress.user_id == user_id,
            UserAddress.is_default == True
        ).first()
        
        # Prepare user preferences
        preferences = {
            'user_id': user_id,
            'full_name': user.full_name,
            'email': user.email,
            'phone': user.phone,
            'role': user.role.value,
            'default_address': {
                'address': default_address.address_line_1 if default_address else None,
                'city': default_address.city if default_address else None,
                'latitude': default_address.latitude if default_address else None,
                'longitude': default_address.longitude if default_address else None
            } if default_address else None
        }
        
        # Store in Redis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            redis_client.set(
                f"user_preferences:{user_id}",
                preferences,
                expire=3600
            )
        )
        loop.close()
        
        logger.info(f"User preferences synced", user_id=user_id)
        return True
        
    except Exception as e:
        logger.error(f"Failed to sync user preferences", user_id=user_id, error=str(e))
        return False
    finally:
        db.close()


@celery_app.task
def send_account_deletion_confirmation(user_id: int):
    '''Send confirmation email for account deletion'''
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        email_subject = "Account Deletion Confirmation"
        email_body = f"""
        Hi {user.full_name},
        
        Your account has been successfully deleted.
        
        All your personal information has been removed from our system.
        
        If you didn't request this deletion or want to restore your account,
        please contact our support team within 30 days.
        
        We're sorry to see you go!
        
        Best regards,
        Food Delivery Team
        """
        
        current_app.send_task(
            "app.tasks.notification_tasks.send_email_notification",
            args=[user.email, email_subject, "account_deleted", {
                "user": user.full_name
            }]
        )
        
        logger.info(f"Account deletion confirmation sent", user_id=user_id)
        return True
        
    except Exception as e:
        logger.error(f"Failed to send deletion confirmation", user_id=user_id, error=str(e))
        return False
    finally:
        db.close()


@celery_app.task
def cleanup_unverified_users():
    '''Delete unverified users after 7 days'''
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        unverified_users = db.query(User).filter(
            User.is_verified == False,
            User.created_at < cutoff_date
        ).all()
        
        deleted_count = 0
        for user in unverified_users:
            db.delete(user)
            deleted_count += 1
        
        db.commit()
        logger.info(f"Cleaned up {deleted_count} unverified users")
        return deleted_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to cleanup unverified users", error=str(e))
        return 0
    finally:
        db.close()


@celery_app.task
def generate_user_report(user_id: int):
    '''Generate user activity report'''
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        from app.models.order import Order
        
        # Get user statistics
        total_orders = db.query(Order).filter(Order.customer_id == user_id).count()
        
        total_spent = db.query(func.sum(Order.total_amount)).filter(
            Order.customer_id == user_id
        ).scalar() or 0
        
        # Get favorite restaurants
        favorite_restaurants = db.query(
            Order.restaurant_id,
            func.count(Order.id).label('order_count')
        ).filter(
            Order.customer_id == user_id
        ).group_by(Order.restaurant_id).order_by(
            func.count(Order.id).desc()
        ).limit(5).all()
        
        report = {
            'user_id': user_id,
            'username': user.username,
            'member_since': user.created_at.isoformat(),
            'total_orders': total_orders,
            'total_spent': float(total_spent),
            'average_order_value': float(total_spent / total_orders) if total_orders > 0 else 0,
            'favorite_restaurants': [
                {'restaurant_id': r[0], 'orders': r[1]} 
                for r in favorite_restaurants
            ],
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Store report in Redis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            redis_client.set(
                f"user_report:{user_id}",
                report,
                expire=86400  # 24 hours
            )
        )
        loop.close()
        
        logger.info(f"User report generated", user_id=user_id)
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate user report", user_id=user_id, error=str(e))
        return None
    finally:
        db.close()


@celery_app.task
def send_promotional_email_to_inactive_users():
    '''Send promotional emails to users who haven't ordered in 30 days'''
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        from app.models.order import Order
        
        # Find users with no recent orders
        recent_order_user_ids = db.query(Order.customer_id).filter(
            Order.created_at > cutoff_date
        ).distinct().subquery()
        
        inactive_users = db.query(User).filter(
            User.is_active == True,
            ~User.id.in_(recent_order_user_ids)
        ).limit(100).all()  # Process in batches
        
        sent_count = 0
        for user in inactive_users:
            email_subject = "We Miss You! Special Offer Inside"
            current_app.send_task(
                "app.tasks.notification_tasks.send_email_notification",
                args=[user.email, email_subject, "promotional_comeback", {
                    "user": user.full_name,
                    "discount_code": "COMEBACK20"
                }]
            )
            sent_count += 1
        
        logger.info(f"Sent promotional emails to {sent_count} inactive users")
        return sent_count
        
    except Exception as e:
        logger.error(f"Failed to send promotional emails", error=str(e))
        return 0
    finally:
        db.close()


@celery_app.task
def batch_update_user_stats():
    '''Update user statistics in batch (scheduled task)'''
    db = SessionLocal()
    try:
        from app.models.order import Order, OrderStatus
        
        # Get all active users
        users = db.query(User).filter(User.is_active == True).all()
        
        updated_count = 0
        for user in users:
            # Calculate stats
            total_orders = db.query(Order).filter(
                Order.customer_id == user.id,
                Order.status == OrderStatus.DELIVERED
            ).count()
            
            total_spent = db.query(func.sum(Order.total_amount)).filter(
                Order.customer_id == user.id,
                Order.status == OrderStatus.DELIVERED
            ).scalar() or 0
            
            # Store in Redis
            stats = {
                'total_orders': total_orders,
                'total_spent': float(total_spent),
                'last_updated': datetime.utcnow().isoformat()
            }
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                redis_client.set(
                    f"user_stats:{user.id}",
                    stats,
                    expire=86400
                )
            )
            loop.close()
            
            updated_count += 1
        
        logger.info(f"Updated stats for {updated_count} users")
        return updated_count
        
    except Exception as e:
        logger.error(f"Failed to batch update user stats", error=str(e))
        return 0
    finally:
        db.close()