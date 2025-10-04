from sqlalchemy import create_engine
from app.config import settings
from sqlalchemy.orm import declarative_base , sessionmaker

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,                 # Auto check connection health before using
    pool_recycle=300,                   # Close and Replace connection older than 300s
    pool_size=5,                        # Number of persistant connection in pool
    max_overflow=0)                     # Extra temporary connection allowed beyond pool_size


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
   
    finally:
        db.close()     