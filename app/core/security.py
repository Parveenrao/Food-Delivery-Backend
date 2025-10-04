from datetime import datetime , timedelta
from typing import Optional
from jose import JWTError , jwt
from passlib.context import CryptContext
from fastapi import HTTPException , status
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"] , depreacted = "auto")

def get_hash_password(password :str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password : str  , hashed_password : str) -> str:
    return pwd_context.verify(plain_password , hashed_password)

def create_access_token(data : dict , expire_delta : Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expire_delta:
        expire = datetime.now() + expire_delta
    
    else:
        expire = datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp":"expire"})
    
    encoded_jwt = jwt.encode(to_encode , settings.SECRET_KEY , algorithm=settings.ALGORITHM)
    
    return encoded_jwt

def verify_token(token:dict) -> dict:
    try:
        payload = jwt.decode(token , settings.SECRET_KEY , algorithms=settings.ALGORITHM)
        return payload
    
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail="Could not validate credentials" ,  
                            headers={"WWW-Authenticate": "Bearer"})
                
        