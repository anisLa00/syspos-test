from fastapi import APIRouter, Path, Query
from models import Product, ProductCreate, ProductUpdate
from fastapi import APIRouter
from contextlib import closing
from database import connect_db
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/products", response_model=Product, status_code=201)
def create_product(product: ProductCreate):
    price_cents = int(product.price * 100)

    with closing(connect_db()) as db:
        sql = """
        INSERT INTO products (sku, name, price_cents, stock_qty, is_active)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(sku) DO NOTHING
        RETURNING id, created_at
        """
        values = (
            product.sku,
            product.name,
            price_cents,
            product.stock_qty,
            product.is_active,
        )
        row = db.execute(sql, values).fetchone()
        db.commit()

    if row is None:
        return JSONResponse(
        status_code=409,
        content={"error": "duplicate_sku", "message": "SKU already exists"},
    )

    product_id, created_at = row

    return Product(
        id=product_id,
        sku=product.sku,
        name=product.name,
        price=product.price,
        stock_qty=product.stock_qty,
        is_active=product.is_active,
        created_at=created_at,
    )
        






