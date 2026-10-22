from fastapi import FastAPI, Request, Form, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import date

from app.database import SessionLocal
from app import models
from app.schemas import TransactionCreate
from app.security import get_password_hash, verify_password, create_session_token, get_current_user

app = FastAPI(title="E&R Management")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- Authentication Routes ----------------
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...), password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(request, "login.html", {
            "request": request, "error": "نام کاربری یا رمز عبور اشتباه است."
        })
    
    token = create_session_token(user.username)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=86400)
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"request": request})

@app.post("/register")
async def register(
    request: Request,
    username: str = Form(...), password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        return templates.TemplateResponse(request, "register.html", {
            "request": request, "error": "این نام کاربری قبلاً ثبت شده است."
        })
    
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

# ---------------- Protected Dashboard Routes ----------------
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    total_income = db.query(func.sum(models.Transaction.amount)).filter(models.Transaction.type == "income").scalar() or 0
    total_expense = db.query(func.sum(models.Transaction.amount)).filter(models.Transaction.type == "expense").scalar() or 0
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
        
    total_income = db.query(func.sum(models.Transaction.amount)).filter(models.Transaction.type == "income").scalar() or 0
    total_expense = db.query(func.sum(models.Transaction.amount)).filter(models.Transaction.type == "expense").scalar() or 0
    balance = total_income - total_expense
    
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request, "total_income": total_income, "total_expense": total_expense,
        "balance": balance, "currency": "AFN", "lang": "en", "user": user
    })

# ---------------- Protected Transaction Routes ----------------
@app.get("/transactions", response_class=HTMLResponse)
async def list_transactions(request: Request, type: str = None, search: str = None, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    query = db.query(models.Transaction)
    
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
        "request": request, "lang": "fa", "transactions": transactions,
        "currency": "AFN", "current_filter": type, "current_search": search, "user": user
    })

@app.get("/transactions/new", response_class=HTMLResponse)
async def new_transaction_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    return templates.TemplateResponse(request, "transaction_form.html", {
        "request": request, "lang": "fa", "today": date.today().isoformat(), "is_edit": False
    })

@app.post("/transactions/new")
async def create_transaction(
    request: Request, type: str = Form(...), amount: float = Form(...),
    category: str = Form(...), description: str = Form(None),
    transaction_date: str = Form(...), db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    try:
        tx_data = TransactionCreate(
            type=type, amount=amount, category=category, description=description,
            transaction_date=date.fromisoformat(transaction_date)
        )
        new_tx = models.Transaction(**tx_data.model_dump())
        db.add(new_tx)
        db.commit()
        return RedirectResponse(url="/transactions", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(request, "transaction_form.html", {
            "request": request, "lang": "fa", "today": transaction_date, 
            "error": f"خطا در ثبت: {str(e)}", "is_edit": False
        })

@app.get("/transactions/{transaction_id}/edit", response_class=HTMLResponse)
async def edit_transaction_form(transaction_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx:
        return RedirectResponse(url="/transactions", status_code=303)
    
    return templates.TemplateResponse(request, "transaction_form.html", {
        "request": request, "lang": "fa", "today": tx.transaction_date.isoformat(),
        "tx": tx, "is_edit": True
    })

@app.post("/transactions/{transaction_id}/edit")
async def update_transaction(
    transaction_id: int, request: Request, type: str = Form(...), amount: float = Form(...),
    category: str = Form(...), description: str = Form(None),
    transaction_date: str = Form(...), db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
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
        return RedirectResponse(url="/transactions", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(request, "transaction_form.html", {
            "request": request, "lang": "fa", "today": transaction_date,
            "tx": tx, "is_edit": True, "error": f"خطا در ویرایش: {str(e)}"
        })

@app.get("/transactions/{transaction_id}/delete")
async def delete_transaction(transaction_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if tx:
        db.delete(tx)
        db.commit()
    return RedirectResponse(url="/transactions", status_code=303)

@app.get("/health")
async def health():
    return {"status": "ok", "app": "E&R Management"}