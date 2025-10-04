from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.order import OrderStatus, PaymentStatus

class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int
    special_instructions: Optional[str] = None

class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int
    quantity: int
    unit_price: float
    total_price: float
    special_instructions: Optional[str] = None

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    restaurant_id: int
    delivery_address: str
    delivery_latitude: Optional[float] = None
    delivery_longitude: Optional[float] = None
    delivery_instructions: Optional[str] = None
    items: List[OrderItemCreate]

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    delivery_partner_id: Optional[int] = None

class OrderResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    restaurant_id: int
    delivery_partner_id: Optional[int] = None
    status: OrderStatus
    payment_status: PaymentStatus
    subtotal: float
    delivery_fee: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    delivery_address: str
    estimated_delivery_time: Optional[datetime] = None
    created_at: datetime
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True