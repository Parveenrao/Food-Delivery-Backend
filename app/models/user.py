from sqlalchemy import Column , String , Boolean , DateTime , Enum , Integer , Float , ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from enum import Enum as PyEnum

class UserRole(PyEnum):
    CUSTOMER  = "customer"
    RESTAURANT_OWNER = 'restaurant_owner'
    DELIVERY_PARTNER = 'delivery_partner'
    ADMIN =  "admin"
    
    
class User(Base):
    __table_name__ = "users"
    
    id = Column(Integer , primary_key=True , index = True , autoincrement=True)
    email = Column(String , unique=True , index=True , nullable=False)
    usename = Column(String , unique=True , index = True , nullable=False)
    full_name = Column(String , nullable=False)
    phone = Column(String , unique=True)
    hashed_password = Column(String , nullable=False)
    role = Column(Enum(UserRole) , default=UserRole.CUSTOMER)
    is_active = Column(Boolean , default=True)
    is_verified = Column(Boolean , default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())   
    
    # Relationship
    
    addressess = relationship("UserAddress" , back_populates = "user")
    orders = relationship("Order", back_populates="customer", foreign_keys="Order.customer_id")
    restaurants = relationship("Restaurant", back_populates="owner")
    payments = relationship("Payment", back_populates="user")
    

class UserAddress(Base):
    __tablename__ = "user_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)  # Home, Work, etc.
    address_line_1 = Column(String, nullable=False)
    address_line_2 = Column(String)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    postal_code = Column(String, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="addresses")    