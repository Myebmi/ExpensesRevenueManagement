from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # رابطه یک‌به‌چند با معاملات
    transactions = relationship("Transaction", back_populates="owner")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    transaction_date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # کلید خارجی: این معامله متعلق به کدام کاربر است؟
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # رابطه با کاربر
    owner = relationship("User", back_populates="transactions")

    __table_args__ = (
        CheckConstraint("type IN ('income', 'expense')", name="check_transaction_type"),
        CheckConstraint("amount > 0", name="check_positive_amount"),
    )