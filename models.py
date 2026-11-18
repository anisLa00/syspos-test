from pydantic import BaseModel,Field
from decimal import Decimal
import datetime
from enum import Enum

class product(BaseModel):
    id:int
    sku:str
    name:str
    price:Decimal = Field(gt=0, decimal_places=2)
    stock_qty: int = Field(ge=0)
    is_active:bool = True
    created_at: datetime

class OrderStatus(str, Enum):
    PAID = "PAID"
    CANCELLED = "CANCELLED"

class Order(BaseModel):
    id: int
    status: OrderStatus
    total_amount: Decimal
    created_at: datetime

class OrderItem(BaseModel):
    id: int
    order_id: int
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Decimal
    line_total: Decimal


