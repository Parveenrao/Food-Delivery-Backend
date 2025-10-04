from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.restaurant import RestaurantStatus

class MenuCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0

class MenuCategoryCreate(MenuCategoryBase):
    pass

class MenuCategoryResponse(MenuCategoryBase):
    id: int
    restaurant_id: int
    is_active: bool

    class Config:
        from_attributes = True

class MenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    discounted_price: Optional[float] = None
    image_url: Optional[str] = None
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_available: bool = True
    preparation_time: int = 15

class MenuItemCreate(MenuItemBase):
    category_id: int

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    discounted_price: Optional[float] = None
    image_url: Optional[str] = None
    is_vegetarian: Optional[bool] = None
    is_vegan: Optional[bool] = None
    is_available: Optional[bool] = None
    preparation_time: Optional[int] = None
    category_id: Optional[int] = None

class MenuItemResponse(MenuItemBase):
    id: int
    restaurant_id: int
    category_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RestaurantBase(BaseModel):
    name: str
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    delivery_fee: float = 0.0
    minimum_order: float = 0.0
    delivery_time: int = 30

class RestaurantCreate(RestaurantBase):
    pass

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[RestaurantStatus] = None
    delivery_fee: Optional[float] = None
    minimum_order: Optional[float] = None
    delivery_time: Optional[int] = None

class RestaurantResponse(RestaurantBase):
    id: int
    owner_id: int
    status: RestaurantStatus
    rating: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RestaurantDetailResponse(RestaurantResponse):
    menu_items: List[MenuItemResponse] = []
    categories: List[MenuCategoryResponse] = []

    class Config:
        from_attributes = True