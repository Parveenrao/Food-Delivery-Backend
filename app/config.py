from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    
    PROJECT_NAME : str  ="Food Delivery System"
    ENV : str = 'development'
    
    #DataBase
    DATABASE_URL : str  = "sqlite:///./food_delivery.db"
    TEST_DATABASE_URL : str = "sqlite:///./food_delivery_test.db"
    
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY : str
    ALGORITHM : str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES : int = 30
    
    # Celery
    CELERY_BROKER_URL : str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND : str = "redis://localhost:6379/0"
    
    # Payment
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str  
    
    
    # Environment
    Environment : str = "development"
    DEBUG: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        

settings = Settings()