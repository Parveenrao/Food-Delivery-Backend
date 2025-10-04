from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.user import User, UserAddress, UserRole
from app.core.security import get_password_hash, verify_password
from app.core.exception import ValidationException, NotFoundException
from app.core.logging import logger
from app.utils.helpers import validate_email, validate_phone, format_phone


class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(
        self, 
        email: str, 
        username: str, 
        password: str, 
        full_name: str,
        phone: Optional[str] = None,
        role: UserRole = UserRole.CUSTOMER
    ) -> User:
        
        
        # Validate email
        if not validate_email(email):
            raise ValidationException("Invalid email format")
        
        # Validate phone if provided
        if phone and not validate_phone(phone):
            raise ValidationException("Invalid phone number format")
        
        # Check if user exists
        existing_user = self.db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing_user:
            if existing_user.email == email:
                raise ValidationException("Email already registered")
            else:
                raise ValidationException("Username already taken")
        
        # Hash password
        hashed_password = get_password_hash(password)
       
        if phone:
            phone = format_phone(phone)
        
        
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            phone=phone,
            role=role
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"User created", user_id=user.id, email=email)
        
        return user
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        
        
        user = self.db.query(User).filter(User.username == username).first()
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        logger.info(f"User authenticated", user_id=user.id)
        
        return user
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
     
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
    
        return self.db.query(User).filter(User.username == username).first()
    
    def update_user(self, user_id: int, **kwargs) -> User:
      
        
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User")
        
        
        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                if key == 'password':
                    setattr(user, 'hashed_password', get_password_hash(value))
                elif key == 'phone':
                    setattr(user, key, format_phone(value))
                else:
                    setattr(user, key, value)
        
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"User updated", user_id=user_id)
        
        return user
    
    def deactivate_user(self, user_id: int) -> bool:
       
        
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User")
        
        user.is_active = False
        self.db.commit()
        
        logger.info(f"User deactivated", user_id=user_id)
        
        return True
    
    def verify_user_email(self, user_id: int) -> bool:
        
        
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User")
        
        user.is_verified = True
        self.db.commit()
        
        logger.info(f"User email verified", user_id=user_id)
        
        return True
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
      
        
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User")
        
        if not verify_password(old_password, user.hashed_password):
            raise ValidationException("Incorrect current password")
        
        user.hashed_password = get_password_hash(new_password)
        self.db.commit()
        
        logger.info(f"Password changed", user_id=user_id)
        
        return True
    
    def get_user_addresses(self, user_id: int) -> List[UserAddress]:
        
        
        return self.db.query(UserAddress).filter(
            UserAddress.user_id == user_id
        ).order_by(UserAddress.is_default.desc()).all()
    
    def add_user_address(self, user_id: int, address_data: dict) -> UserAddress:
        
        
        # If this is default, unset other defaults
        if address_data.get('is_default'):
            self.db.query(UserAddress).filter(
                UserAddress.user_id == user_id,
                UserAddress.is_default == True
            ).update({"is_default": False})
        
        address = UserAddress(user_id=user_id, **address_data)
        self.db.add(address)
        self.db.commit()
        self.db.refresh(address)
        
        logger.info(f"Address added", user_id=user_id, address_id=address.id)
        
        return address