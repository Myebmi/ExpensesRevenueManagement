from app import models  # noqa: F401
from app.database import Base, engine

# این دستور تمام مدل‌هایی که از Base ارث‌بری کرده‌اند را در دیتابیس می‌سازد
Base.metadata.create_all(bind=engine)

print("✅ دیتابیس و جداول با موفقیت ساخته شدند!")