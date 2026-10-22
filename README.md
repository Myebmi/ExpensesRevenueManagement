# E&R Management | مدیریت عواید و مصارف

یک وب‌اپلیکیشن حرفه‌ای و امن برای ثبت و مدیریت عواید و مصارف روزانه و کسب‌وکارهای کوچک.

## ✨ ویژگی‌های کلیدی
- **مدیریت معاملات:** ثبت، ویرایش، حذف و جستجوی پیشرفته عواید و مصارف.
- **داشبورد هوشمند:** محاسبه لحظه‌ای مجموع عواید، مصارف و بیلانس.
- **امنیت بالا:** سیستم احراز هویت با هش کردن رمز عبور و مدیریت نشست (Session).
- **دو زبانه:** رابط کاربری کامل به زبان‌های فارسی (RTL) و انگلیسی (LTR).
- **واکنش‌گرا:** طراحی سازگار با موبایل، تبلت و کمپیوتر.
- **مستندسازی و تست:** دارای تست‌های خودکار با Pytest.

## 🛠️ فناوری‌های استفاده شده
- **Backend:** Python 3.12, FastAPI
- **Database:** PostgreSQL 16
- **ORM:** SQLAlchemy
- **Frontend:** HTML5, CSS3, Jinja2
- **Security:** Passlib (pbkdf2_sha256), Session Cookies
- **DevOps:** Docker, Docker Compose
- **Testing:** Pytest, HTTPX

## 🚀 نصب و اجرا (Local)

### پیش‌نیازها
- Docker Desktop (نصب شده و در حال اجرا)
- Git

### مراحل اجرا
1. پروژه را کلون کنید:
   ```bash
   git clone https://github.com/Myebmi/er-management.git
   cd er-management