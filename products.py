from fastapi import APIRouter, Path, Query
from models import Product, ProductCreate, ProductUpdate,StockAdjustment
from fastapi import APIRouter
from contextlib import closing
from database import connect_db
from fastapi.responses import JSONResponse
from decimal import Decimal

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

@router.get("/products", response_model=list[Product])
def list_products():
    with closing(connect_db()) as db:
        rows = db.execute(
            """
            SELECT id, sku, name, price_cents, stock_qty, is_active, created_at
            FROM products
            ORDER BY id
            """
        ).fetchall()

    products = []
    for product_id, sku, name, cents, stock_qty, is_active, created_at in rows:
        products.append(
            Product(
                id=product_id,
                sku=sku,
                name=name,
                price=Decimal(cents).scaleb(-2),
                stock_qty=stock_qty,
                is_active=bool(is_active),
                created_at=created_at,
            )
        )
    return products


@router.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int = Path(ge=1, le=2**63 - 1)):
    with closing(connect_db()) as db:
        row = db.execute(
            """
            SELECT id, sku, name, price_cents, stock_qty, is_active, created_at
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()

    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": "product_not_found", "message": "Product not found"},
        )

    product_id, sku, name, cents, stock_qty, is_active, created_at = row
    return Product(
        id=product_id,
        sku=sku,
        name=name,
        price=Decimal(cents).scaleb(-2),
        stock_qty=stock_qty,
        is_active=bool(is_active),
        created_at=created_at,
    )
    
@router.patch("/products/{product_id}", response_model=Product)
def update_product(
    update: ProductUpdate,
    product_id: int = Path(ge=1, le=2**63 - 1),
):
    changes = update.model_dump(exclude_unset=True)
    if None in changes.values():
        return JSONResponse(
            status_code=422,
            content={"error": "null_field", "message": "Send a value or omit the field"},
        )

    price = update.price
    price_cents = None
    if price is not None:
        if price > Decimal("92233720368547758.07"):
            return JSONResponse(
                status_code=422,
                content={"error": "invalid_price", "message": "Price is too large"},
            )
        price_cents = int(price * 100)

    with closing(connect_db()) as db:
        row = db.execute(
            """
            UPDATE products
            SET name = COALESCE(?, name),
                price_cents = COALESCE(?, price_cents),
                is_active = COALESCE(?, is_active)
            WHERE id = ?
            RETURNING id, sku, name, price_cents, stock_qty, is_active, created_at
            """,
            (update.name, price_cents, update.is_active, product_id),
        ).fetchone()
        db.commit()

    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": "product_not_found", "message": "Product not found"},
        )

    product_id, sku, name, cents, stock_qty, is_active, created_at = row

    return Product(
        id=product_id,
        sku=sku,
        name=name,
        price=Decimal(cents).scaleb(-2),
        stock_qty=stock_qty,
        is_active=bool(is_active),
        created_at=created_at,
    )   

@router.post("/products/{product_id}/stock-adjustments", response_model=Product)
def adjust_stock(
    adjustment: StockAdjustment,
    product_id: int = Path(ge=1, le=2**63 - 1),
):
    with closing(connect_db()) as db:
        db.execute("BEGIN IMMEDIATE")

        row = db.execute(
            """
            SELECT id, sku, name, price_cents, stock_qty, is_active, created_at
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()

        if row is None:
            error = {"error": "product_not_found", "message": "Product not found"}
            return JSONResponse(status_code=404, content=error)

        product_id, sku, name, cents, stock_qty, is_active, created_at = row
        new_stock = stock_qty + adjustment.delta

        if new_stock < 0:
            error = {"error": "invalid_stock", "message": "Stock cannot go below zero"}
            return JSONResponse(status_code=400, content=error)

        if new_stock > 2**63 - 1:
            error = {"error": "invalid_stock", "message": "Stock is too large"}
            return JSONResponse(status_code=400, content=error)

        db.execute(
            "UPDATE products SET stock_qty = ? WHERE id = ?",
            (new_stock, product_id),
        )
        db.commit()

    return Product(
        id=product_id,
        sku=sku,
        name=name,
        price=Decimal(cents).scaleb(-2),
        stock_qty=new_stock,
        is_active=bool(is_active),
        created_at=created_at,
    )     
        






