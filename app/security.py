import os
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
from itsdangerous import BadData, URLSafeTimedSerializer
from fastapi import Request
from sqlalchemy.orm import Session
from app import models

# تنظیمات هش کردن رمز عبور با الگوریتم pbkdf2_sha256
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# خواندن کلید مخفی از فایل .env (متغیر محیطی)
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-key-for-dev-only")

def get_password_hash(password: str) -> str:
    """تبدیل رمز عبور ساده به هش امن"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """بررسی تطابق رمز وارد شده با هش ذخیره شده"""
    return pwd_context.verify(plain_password, hashed_password)

def create_session_token(username: str) -> str:
    """ساخت توکن امن برای ذخیره در کوکی"""
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(username, salt="session-cookie")

def get_current_user(request: Request, db: Session) -> models.User | None:
    """خواندن کاربر فعلی از کوکی (برای محافظت از صفحات)"""
    token = request.cookies.get("session_token")
    if not token:
        return None
    
    try:
        serializer = URLSafeTimedSerializer(SECRET_KEY)
        username = serializer.loads(token, salt="session-cookie", max_age=86400)
        return db.query(models.User).filter(models.User.username == username).first()
    except BadData:
        return None