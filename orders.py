from contextlib import closing
from decimal import Decimal

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from fastapi import APIRouter, Path

from database import connect_db
from models import OrderCreate, OrderItem, OrderResponse

router = APIRouter()
SQLITE_MAX_INT = 2**63 - 1


def order_error(status_code, code, message):
    return JSONResponse(
        status_code=status_code,
        content={"error": code, "message": message},
    )


@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(order: OrderCreate):
    quantities = {}
    for item in order.items:
        product_id = item.product_id
        quantities[product_id] = quantities.get(product_id, 0) + item.quantity

    with closing(connect_db()) as db:
        db.execute("BEGIN IMMEDIATE")

        lines = []
        total_cents = 0

        for product_id, quantity in quantities.items():
            if product_id > SQLITE_MAX_INT:
                return order_error(404, "product_not_found", "Product not found")

            row = db.execute(
                "SELECT price_cents, stock_qty, is_active FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()

            if row is None:
                return order_error(404, "product_not_found", "Product not found")

            price_cents, stock_qty, is_active = row
            if not is_active:
                return order_error(409, "product_inactive", "Product is inactive")
            if quantity > stock_qty:
                return order_error(409, "insufficient_stock", "Not enough stock")

            line_total_cents = quantity * price_cents
            total_cents += line_total_cents
            lines.append((product_id, quantity, price_cents, line_total_cents))

        if total_cents > SQLITE_MAX_INT:
            return order_error(400, "invalid_total", "Order total is too large")

        order_id, created_at = db.execute(
            """
            INSERT INTO orders (status, total_amount_cents)
            VALUES (?, ?)
            RETURNING id, created_at
            """,
            ("PAID", total_cents),
        ).fetchone()

        items = []
        for product_id, quantity, price_cents, line_total_cents in lines:
            item_id = db.execute(
                """
                INSERT INTO order_items
                    (order_id, product_id, quantity, unit_price_cents, line_total_cents)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, product_id, quantity, price_cents, line_total_cents),
            ).lastrowid

            db.execute(
                "UPDATE products SET stock_qty = stock_qty - ? WHERE id = ?",
                (quantity, product_id),
            )

            items.append(
                OrderItem(
                    id=item_id,
                    order_id=order_id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=Decimal(price_cents).scaleb(-2),
                    line_total=Decimal(line_total_cents).scaleb(-2),
                )
            )

        response = OrderResponse(
            id=order_id,
            status="PAID",
            total_amount=Decimal(total_cents).scaleb(-2),
            created_at=created_at,
            items=items,
        )
        db.commit()

    return response


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int = Path(ge=1, le=SQLITE_MAX_INT)):
    with closing(connect_db()) as db:
        order_row = db.execute(
            "SELECT status, total_amount_cents, created_at FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()

        if order_row is None:
            return order_error(404, "order_not_found", "Order not found")

        item_rows = db.execute(
            """
            SELECT id, product_id, quantity, unit_price_cents, line_total_cents
            FROM order_items
            WHERE order_id = ?
            ORDER BY id
            """,
            (order_id,),
        ).fetchall()

    status, total_cents, created_at = order_row
    items = []

    for item_id, product_id, quantity, price_cents, line_total_cents in item_rows:
        items.append(
            OrderItem(
                id=item_id,
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=Decimal(price_cents).scaleb(-2),
                line_total=Decimal(line_total_cents).scaleb(-2),
            )
        )

    return OrderResponse(
        id=order_id,
        status=status,
        total_amount=Decimal(total_cents).scaleb(-2),
        created_at=created_at,
        items=items,
    )


@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int = Path(ge=1, le=SQLITE_MAX_INT)):
    with closing(connect_db()) as db:
        db.execute("BEGIN IMMEDIATE")

        order_row = db.execute(
            "SELECT status FROM orders WHERE id = ?", (order_id,)
        ).fetchone()

        if order_row is None:
            return order_error(404, "order_not_found", "Order not found")
        if order_row[0] == "CANCELLED":
            return order_error(409, "order_already_cancelled", "Order already cancelled")

        items = db.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()

        for product_id, quantity in items:
            updated = db.execute(
                """
                UPDATE products
                SET stock_qty = stock_qty + ?
                WHERE id = ? AND stock_qty <= ?
                """,
                (quantity, product_id, SQLITE_MAX_INT - quantity),
            )
            if updated.rowcount == 0:
                db.rollback()
                return order_error(409, "stock_limit", "Could not restore stock")

        db.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            ("CANCELLED", order_id),
        )
        db.commit()

    return {"id": order_id, "status": "CANCELLED"}
