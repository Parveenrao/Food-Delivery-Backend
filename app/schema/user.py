from pydantic import BaseModel , EmailStr
from typing import Optional , List
from datetime import datetime
from app.models.user import UserRole

class UserBase(BaseModel):
    email : EmailStr
    username : str
    full_name : str
    phone : Optional[str] = None
    
class UserCreate(UserBase):
    password : str 
    role : UserRole = UserRole.CUSTOMER
    
class UserUpdate(BaseModel):
    full_name : str[Optional] = None
    phone : Optional[str] = None
    
class UserResponse(BaseModel):
    id : int
    role : UserRole
    is_active : bool
    is_verified : bool
    created_at : datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username : str
    password : str   


class Token(BaseModel):
    access_token : str  
    token_type :  str        
    user : UserResponse
    
class AddressBase(BaseModel):
    title: str
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool = False
    
 
class AddressCreate(AddressBase):
    pass      

class AddressResponse(AddressBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
    
    