from pydantic import BaseModel,Field,ConfigDict,field_validator
from decimal import Decimal
from datetime import datetime
from enum import Enum

class Product(BaseModel):
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

class ProductCreate(BaseModel):
    sku: str = Field(min_length=1)
    name: str = Field(min_length=1)
    price: Decimal = Field(gt=0, decimal_places=2)
    stock_qty: int = Field(ge=0)
    is_active: bool = True

class ProductUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = Field(default=None, min_length=1)
    price: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    is_active: bool | None = None

class StockAdjustment(BaseModel):
    delta: int
    reason: str = Field(min_length=1)    



