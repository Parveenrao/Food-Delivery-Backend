from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.core.security import verify_token
from app.core.exception import AuthenticationException, AuthorizationException

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    '''Get current authenticated user'''
    token = credentials.credentials
    payload = verify_token(token)
    
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationException("Invalid token")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise AuthenticationException("User not found")
    
    if not user.is_active:
        raise AuthenticationException("User account is inactive")
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    '''Get current active user'''
    if not current_user.is_active:
        raise AuthenticationException("User account is inactive")
    return current_user

def require_role(*allowed_roles: UserRole):
    '''Dependency to require specific user roles'''
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AuthorizationException(
                f"Access denied. Required roles: {[role.value for role in allowed_roles]}"
            )
        return current_user
    return role_checker

# Role-specific dependencies
def get_customer(current_user: User = Depends(require_role(UserRole.CUSTOMER))) -> User:
    return current_user

def get_restaurant_owner(current_user: User = Depends(require_role(UserRole.RESTAURANT_OWNER))) -> User:
    return current_user

def get_delivery_partner(current_user: User = Depends(require_role(UserRole.DELIVERY_PARTNER))) -> User:
    return current_user

def get_admin(current_user: User = Depends(require_role(UserRole.ADMIN))) -> User:
    return current_user