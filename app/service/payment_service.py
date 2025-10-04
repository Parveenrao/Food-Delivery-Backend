import stripe
from sqlalchemy.orm import Session
from app.config import settings
from app.models.payment import Payment, PaymentStatus, PaymentMethod
from app.models.order import Order
from app.core.logging import logger
from typing import Optional
import datetime

stripe.api_key = settings.stripe_secret_key

class PaymentService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_payment_intent(self, order_id: int, payment_method: PaymentMethod) -> Optional[dict]:
        
        try:
            order = self.db.query(Order).filter(Order.id == order_id).first()
            if not order:
                logger.error(f"Order not found", order_id=order_id)
                return None
            
            
            amount_cents = int(order.total_amount * 100)
            
            
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='INR',
                metadata={
                    'order_id': order_id,
                    'customer_id': order.customer_id
                }
            )
            
            
            payment = Payment(
                user_id=order.customer_id,
                order_id=order_id,
                stripe_payment_intent_id=intent.id,
                amount=order.total_amount,
                method=payment_method,
                status=PaymentStatus.PENDING
            )
            
            self.db.add(payment)
            self.db.commit()
            
            logger.info(f"Payment intent created", 
                       order_id=order_id, 
                       payment_intent_id=intent.id)
            
            return {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
                'payment_id': payment.id
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent", error=str(e))
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating payment intent", error=str(e))
            return None
    
    def process_stripe_payment(self, payment: Payment) -> bool:
        
        try:
            if not payment.stripe_payment_intent_id:
                return False
            
            # Retrieve payment intent from Stripe
            intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
            
            if intent.status == 'succeeded':
                payment.status = PaymentStatus.COMPLETED
                self.db.commit()
                logger.info(f"Payment completed", payment_id=payment.id)
                return True
            elif intent.status == 'requires_payment_method':
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = "Payment method required"
                self.db.commit()
                return False
            elif intent.status == 'canceled':
                payment.status = PaymentStatus.CANCELLED
                self.db.commit()
                return False
            
            return False
            
        except stripe.error.StripeError as e:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = str(e)
            self.db.commit()
            logger.error(f"Stripe error processing payment", payment_id=payment.id, error=str(e))
            return False
    
    def check_stripe_payment_status(self, payment_intent_id: str) -> PaymentStatus:
        
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == 'succeeded':
                return PaymentStatus.COMPLETED
            elif intent.status in ['requires_payment_method', 'payment_failed']:
                return PaymentStatus.FAILED
            elif intent.status == 'canceled':
                return PaymentStatus.CANCELLED
            elif intent.status in ['requires_confirmation', 'requires_action']:
                return PaymentStatus.PROCESSING
            else:
                return PaymentStatus.PENDING
                
        except stripe.error.StripeError as e:
            logger.error(f"Error checking payment status", payment_intent_id=payment_intent_id, error=str(e))
            return PaymentStatus.FAILED
    
    def process_refund(self, payment: Payment, refund_amount: Optional[float] = None) -> bool:
        
        try:
            if not payment.stripe_payment_intent_id:
                return False
            
            amount_to_refund = refund_amount or payment.amount
            amount_cents = int(amount_to_refund * 100)
            
            # Create refund
            refund = stripe.Refund.create(
                payment_intent=payment.stripe_payment_intent_id,
                amount=amount_cents
            )
            
            if refund.status == 'succeeded':
                payment.status = PaymentStatus.REFUNDED
                payment.refund_amount = amount_to_refund
                payment.refunded_at = datetime.utcnow()
                self.db.commit()
                
                logger.info(f"Refund processed", payment_id=payment.id, amount=amount_to_refund)
                return True
            
            return False
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error processing refund", payment_id=payment.id, error=str(e))
            return False
