from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.payment import PaymentMethod, PaymentStatus

class PaymentIntentCreate(BaseModel):
    order_id: int
    payment_method: PaymentMethod

class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str

class PaymentResponse(BaseModel):
    id: int
    user_id: int
    order_id: int
    stripe_payment_intent_id: Optional[str] = None
    amount: float
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    failure_reason: Optional[str] = None
    refund_amount: float
    created_at: datetime

    class Config:
        from_attributes = True
