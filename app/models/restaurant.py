from sqlalchemy import Column , String , Boolean , DateTime , Enum , Integer , Float , ForeignKey , Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from enum import Enum as PyEnum

class RestaurantStatus(PyEnum):
    OPEN = "open"
    CLOSED = "closed"
    BUSY = "busy"
    
class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    phone = Column(String)
    email = Column(String)
    address = Column(Text, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    status = Column(Enum(RestaurantStatus), default=RestaurantStatus.OPEN)
    rating = Column(Float, default=0.0)
    delivery_fee = Column(Float, default=0.0)
    minimum_order = Column(Float, default=0.0)
    delivery_time = Column(Integer, default=30)  # in minutes
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())    
    
    # Relationships
    owner = relationship("User", back_populates="restaurants")
    menu_items = relationship("MenuItem", back_populates="restaurant")
    orders = relationship("Order", back_populates="restaurant")
    categories = relationship("MenuCategory", back_populates="restaurant")
    
    
    
class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="categories")
    menu_items = relationship("MenuItem", back_populates="category")
    

class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    discounted_price = Column(Float)
    image_url = Column(String)
    is_vegetarian = Column(Boolean, default=False)
    is_vegan = Column(Boolean, default=False)
    is_available = Column(Boolean, default=True)
    preparation_time = Column(Integer, default=15)  # in minutes
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    category_id = Column(Integer, ForeignKey("menu_categories.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    restaurant = relationship("Restaurant", back_populates="menu_items")
    category = relationship("MenuCategory", back_populates="menu_items")
    order_items = relationship("OrderItem", back_populates="menu_item")        