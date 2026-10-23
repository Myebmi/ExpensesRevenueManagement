# استفاده از نسخه سبک پایتون 3.12
FROM python:3.12-slim

# تنظیم پوشه کاری درون کانتینر
WORKDIR /app

# نصب وابستگی‌های سیستمی لازم برای psycopg
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# کپی کردن فایل نیازمندی‌ها و نصب آن‌ها با تنظیمات شبکه پایدارتر
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# کپی کردن تمام فایل‌های پروژه به داخل کانتینر
COPY . .

# دستور اجرای برنامه
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]