import redis
import json 
from typing import Any , Optional
from app.config import settings
from  app.core.logging import logger


class RedisClient:
    def __init__(self):
        self.redis = redis.from_url(settings.redis_url , decode_response = True)
        
    async def get_key(self , key : str) -> Optional[str]:
        try:
            return self.redis.get(key)    
        
        except Exception as e:
            logger.error(f" Redis GET error :{e}", key=key)
            
            return None
        
    
    async def set(self , key : str , value : Any  , expire : Optional[int] = None) -> bool:
        try:
            if isinstance(value , (dict , list)):
                value = json.dumps(value)
            
            return self.redis.set(key , value , ex = expire)    
        
        except Exception as e:
            logger.error(f"Redis SET error :{e}" , key = key) 
            
            return False
        
    
    async def delete(self , key : str) -> bool:
        try:
            return bool(self.redis.delete(key))
        
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}" , key = key) 
            
            return False
        
    
    async def exist(self , key : str) -> bool:    
        try:
            return bool(self.redis.exist(key))
        
        except Exception as e:
            logger.error(f"Redis EXIST error: {e}" , key = key)
            
            return False      
        

redis_client = RedisClient()        