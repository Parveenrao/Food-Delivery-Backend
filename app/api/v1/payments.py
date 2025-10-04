from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.order import Order
from app.schema.payment import PaymentIntentCreate, PaymentIntentResponse
from app.service.payment_service import PaymentService
from app.task.payment_task import process_payment
from app.core.logging import logger
import stripe
from app.config import settings

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/create-intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    payment_data: PaymentIntentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    '''Create payment intent for an order'''
    # Verify order belongs to current user
    order = db.query(Order).filter(
        Order.id == payment_data.order_id,
        Order.customer_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    payment_service = PaymentService(db)
    result = payment_service.create_payment_intent(
        payment_data.order_id,
        payment_data.payment_method
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create payment intent"
        )
    
    return PaymentIntentResponse(
        client_secret=result['client_secret'],
        payment_intent_id=result['payment_intent_id']
    )

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    '''Handle Stripe webhook events'''
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        order_id = payment_intent['metadata'].get('order_id')
        
        if order_id:
            # Trigger async payment processing
            process_payment.delay(int(order_id))
    
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        order_id = payment_intent['metadata'].get('order_id')
        
        if order_id:
            # Handle failed payment
            logger.error(f"Payment failed for order", order_id=order_id)
    
    return {"status": "success"}

@router.get("/my-payments")
async def get_my_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    '''Get current user's payment history'''
    from app.models.payment import Payment
    
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.id
    ).order_by(Payment.created_at.desc()).all()
    
    return payments