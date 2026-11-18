from contextlib import closing
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Query

from database import connect_db
from models import DailySalesReport, TopSellingProduct

router = APIRouter()


@router.get("/reports/daily-sales", response_model=DailySalesReport)
def daily_sales(day: date = Query(alias="date")):
    day_text = day.isoformat()

    with closing(connect_db()) as db:
        db.execute("BEGIN")

        order_rows = db.execute(
            """
            SELECT total_amount_cents
            FROM orders
            WHERE status = 'PAID' AND date(created_at) = ?
            """,
            (day_text,),
        ).fetchall()

        sold_rows = db.execute(
            """
            SELECT p.id, p.sku, p.name, oi.quantity
            FROM order_items AS oi
            JOIN orders AS o ON o.id = oi.order_id
            JOIN products AS p ON p.id = oi.product_id
            WHERE o.status = 'PAID' AND date(o.created_at) = ?
            """,
            (day_text,),
        ).fetchall()

    total_cents = sum(row[0] for row in order_rows)
    revenue = Decimal(f"{total_cents // 100}.{total_cents % 100:02d}")

    sales = {}
    for product_id, sku, name, quantity in sold_rows:
        if product_id not in sales:
            sales[product_id] = TopSellingProduct(
                product_id=product_id, sku=sku, name=name, quantity_sold=0
            )
        sales[product_id].quantity_sold += quantity

    top_products = sorted(
        sales.values(),
        key=lambda product: (-product.quantity_sold, product.product_id),
    )[:3]

    return DailySalesReport(
        date=day,
        order_count=len(order_rows),
        total_revenue=revenue,
        top_products=top_products,
    )
