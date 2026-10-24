from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exception_handlers import http_exception_handler
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import date
import jdatetime
import csv
import io
import calendar

from app.database import SessionLocal, engine, Base
from app import models
from app.schemas import TransactionCreate
from app.security import get_password_hash, verify_password, create_session_token, get_current_user

app = FastAPI(title="E&R Management")

@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# ==========================================
# فیلتر تاریخ شمسی برای Jinja2
# ==========================================
def to_jalali_filter(gregorian_date):
    if gregorian_date is None:
        return ""
    try:
        jalali_date = jdatetime.date.fromgregorian(date=gregorian_date)
        return jalali_date.strftime("%Y/%m/%d")
    except Exception:
        return str(gregorian_date)

templates.env.filters["to_jalali"] = to_jalali_filter
# ==========================================

# ==========================================
# مدیریت خطای 404 (صفحه اختصاصی)
# ==========================================
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(request, "404.html", {"request": request}, status_code=404)
    return await http_exception_handler(request, exc)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- Auth Routes ----------------
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request, "lang": "fa"})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), lang: str = Form("fa"), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(request, "login.html", {"request": request, "lang": lang, "error": "نام کاربری یا رمز عبور اشتباه است."})
    token = create_session_token(user.username)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=86400)
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"request": request, "lang": "fa"})

@app.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...), lang: str = Form("fa"), db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        return templates.TemplateResponse(request, "register.html", {"request": request, "lang": lang, "error": "این نام کاربری قبلاً ثبت شده است."})
    hashed = get_password_hash(password)
    new_user = models.User(username=username, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_token")
    return response

# ---------------- Dashboard Routes ----------------
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    total_income = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user.id, 
        models.Transaction.type == "income"
    ).scalar() or 0
    total_expense = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user.id, 
        models.Transaction.type == "expense"
    ).scalar() or 0
    balance = total_income - total_expense
    
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request, "total_income": total_income, "total_expense": total_expense,
        "balance": balance, "currency": "AFN", "lang": "fa", "user": user
    })

@app.get("/en", response_class=HTMLResponse)
async def dashboard_en(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    total_income = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user.id, 
        models.Transaction.type == "income"
    ).scalar() or 0
    total_expense = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user.id, 
        models.Transaction.type == "expense"
    ).scalar() or 0
    balance = total_income - total_expense
    
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request, "total_income": total_income, "total_expense": total_expense,
        "balance": balance, "currency": "AFN", "lang": "en", "user": user
    })

# ---------------- Transaction Routes ----------------
@app.get("/transactions", response_class=HTMLResponse)
async def list_transactions(request: Request, type: str = None, search: str = None, lang: str = "fa", db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    query = db.query(models.Transaction).filter(models.Transaction.user_id == user.id)
    
    if type in ["income", "expense"]:
        query = query.filter(models.Transaction.type == type)
        
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.Transaction.category.ilike(search_term),
                models.Transaction.description.ilike(search_term)
            )
        )
        
    transactions = query.order_by(models.Transaction.transaction_date.desc()).all()
    
    return templates.TemplateResponse(request, "transactions_list.html", {
        "request": request, "lang": lang, "transactions": transactions,
        "currency": "AFN", "current_filter": type, "current_search": search, "user": user
    })

@app.get("/transactions/new", response_class=HTMLResponse)
async def new_transaction_form(request: Request, lang: str = "fa", db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    categories = ["فروش روزانه", "فروش عمده", "اجاره", "خرید مواد", "برق و آب", "حقوق کارمندان", "سایر"]
    
    return templates.TemplateResponse(request, "transaction_form.html", {
        "request": request, "lang": lang, "today": date.today().isoformat(), 
        "is_edit": False, "categories": categories
    })

@app.post("/transactions/new")
async def create_transaction(request: Request, type: str = Form(...), amount: float = Form(...), category: str = Form(...), description: str = Form(None), transaction_date: str = Form(...), lang: str = Form("fa"), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    try:
        tx_data = TransactionCreate(
            type=type, amount=amount, category=category, description=description,
            transaction_date=date.fromisoformat(transaction_date)
        )
        new_tx = models.Transaction(**tx_data.model_dump(), user_id=user.id)
        db.add(new_tx)
        db.commit()
        return RedirectResponse(url=f"/transactions?msg=created&lang={lang}", status_code=303)
    except Exception as e:
        categories = ["فروش روزانه", "فروش عمده", "اجاره", "خرید مواد", "برق و آب", "حقوق کارمندان", "سایر"]
        return templates.TemplateResponse(request, "transaction_form.html", {
            "request": request, "lang": lang, "today": transaction_date, 
            "error": f"خطا در ثبت: {str(e)}", "is_edit": False, "categories": categories
        })

@app.get("/transactions/{transaction_id}/edit", response_class=HTMLResponse)
async def edit_transaction_form(transaction_id: int, request: Request, lang: str = "fa", db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    tx = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == user.id
    ).first()
    
    if not tx:
        return RedirectResponse(url="/transactions", status_code=303)
    
    categories = ["فروش روزانه", "فروش عمده", "اجاره", "خرید مواد", "برق و آب", "حقوق کارمندان", "سایر"]
    
    return templates.TemplateResponse(request, "transaction_form.html", {
        "request": request, "lang": lang, "today": tx.transaction_date.isoformat(),
        "tx": tx, "is_edit": True, "categories": categories
    })

@app.post("/transactions/{transaction_id}/edit")
async def update_transaction(transaction_id: int, request: Request, type: str = Form(...), amount: float = Form(...), category: str = Form(...), description: str = Form(None), transaction_date: str = Form(...), lang: str = Form("fa"), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    tx = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == user.id
    ).first()
    
    if not tx:
        return RedirectResponse(url="/transactions", status_code=303)

    try:
        tx_data = TransactionCreate(
            type=type, amount=amount, category=category, description=description,
            transaction_date=date.fromisoformat(transaction_date)
        )
        for key, value in tx_data.model_dump().items():
            setattr(tx, key, value)
        db.commit()
        return RedirectResponse(url=f"/transactions?msg=updated&lang={lang}", status_code=303)
    except Exception as e:
        categories = ["فروش روزانه", "فروش عمده", "اجاره", "خرید مواد", "برق و آب", "حقوق کارمندان", "سایر"]
        return templates.TemplateResponse(request, "transaction_form.html", {
            "request": request, "lang": lang, "today": transaction_date,
            "tx": tx, "is_edit": True, "error": f"خطا در ویرایش: {str(e)}", "categories": categories
        })

@app.get("/transactions/{transaction_id}/delete")
async def delete_transaction(transaction_id: int, request: Request, lang: str = "fa", db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    tx = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == user.id
    ).first()
    
    if tx:
        db.delete(tx)
        db.commit()
    return RedirectResponse(url=f"/transactions?msg=deleted&lang={lang}", status_code=303)


# ---------------- Report Routes ----------------
@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, start_date: str = None, end_date: str = None, lang: str = "fa", db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    today = date.today()
    if not start_date:
        start_date = today.replace(day=1).isoformat()
    if not end_date:
        _, last_day = calendar.monthrange(today.year, today.month)
        end_date = today.replace(day=last_day).isoformat()
    
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user.id,
        models.Transaction.transaction_date >= start,
        models.Transaction.transaction_date <= end
    ).order_by(models.Transaction.transaction_date.desc()).all()
    
    total_income = sum(tx.amount for tx in transactions if tx.type == "income")
    total_expense = sum(tx.amount for tx in transactions if tx.type == "expense")
    balance = total_income - total_expense
    
    return templates.TemplateResponse(request, "reports.html", {
        "request": request, "lang": lang, "user": user,
        "transactions": transactions,
        "start_date": start_date, "end_date": end_date,
        "total_income": total_income, "total_expense": total_expense, "balance": balance,
        "currency": "AFN"
    })

@app.get("/reports/export")
async def export_report_csv(request: Request, start_date: str = None, end_date: str = None, lang: str = "fa", db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    if not start_date or not end_date:
        return RedirectResponse(url=f"/reports?lang={lang}", status_code=303)
    
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user.id,
        models.Transaction.transaction_date >= start,
        models.Transaction.transaction_date <= end
    ).order_by(models.Transaction.transaction_date.asc()).all()
    
    output = io.StringIO()
    output.write('\ufeff') 
    writer = csv.writer(output)
    
    writer.writerow(["تاریخ", "نوع", "دسته‌بندی", "مبلغ (AFN)", "توضیحات"])
    
    for tx in transactions:
        type_fa = "عاید" if tx.type == "income" else "مصرف"
        writer.writerow([
            tx.transaction_date.isoformat(),
            type_fa,
            tx.category,
            tx.amount,
            tx.description or ""
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{start_date}_to_{end_date}.csv"}
    )


@app.get("/health")
async def health():
    return {"status": "ok", "app": "E&R Management"}