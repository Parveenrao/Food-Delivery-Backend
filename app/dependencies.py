from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.user import User 
from app.core.logging import logger



def get_current_active_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> User:
   
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

def verify_api_key(api_key: Optional[str] = None) -> bool:
   
   
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
 
    return True