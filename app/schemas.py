from pydantic import BaseModel, Field
from datetime import date
from typing import Literal, Optional

class TransactionCreate(BaseModel):
    type: Literal["income", "expense"]
    amount: float = Field(..., gt=0, description="مبلغ باید بزرگتر از صفر باشد")
    category: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    transaction_date: date