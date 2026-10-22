import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# خواندن آدرس دیتابیس از متغیر محیطی
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./er_management.db")

# تنظیمات برای اتصال به دیتابیس
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()