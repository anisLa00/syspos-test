from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import database
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    schema = Path(database.__file__).with_name("schema.sql").read_text(encoding="utf-8")
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "syspos.db")

    monkeypatch.setenv("SYSPOS_API_KEY", "test-only-key")

    with closing(database.connect_db()) as db:
        db.executescript(schema)

    with TestClient(app, headers={"X-API-Key": "test-only-key"}) as test_client:
        yield test_client


def test_create_order_reduces_stock(client):
    added = client.post(
        "/products",
        json={"sku": "TEST-WATER", "name": "Water", "price": "2.50", "stock_qty": 10},
    )
    assert added.status_code == 201, added.text
    product_id = added.json()["id"]

    order = client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 2}]},
    )
    assert order.status_code == 201, order.text

    product = client.get(f"/products/{product_id}")
    assert product.status_code == 200, product.text
    assert product.json()["stock_qty"] == 8


def add_test_product(client, sku, stock_qty):
    response = client.post(
        "/products",
        json={"sku": sku, "name": sku, "price": "2.50", "stock_qty": stock_qty},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_insufficient_stock_rejects_whole_order(client):
    first_id = add_test_product(client, "TEST-WATER", 10)
    second_id = add_test_product(client, "TEST-TEA", 1)

    rejected = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": first_id, "quantity": 2},
                {"product_id": second_id, "quantity": 2},
            ]
        },
    )
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["error"] == "insufficient_stock"

    assert client.get(f"/products/{first_id}").json()["stock_qty"] == 10
    assert client.get(f"/products/{second_id}").json()["stock_qty"] == 1

    with closing(database.connect_db()) as db:
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


def test_cancel_order_restores_stock(client):
    product_id = add_test_product(client, "TEST-CANCEL", 10)

    order = client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 2}]},
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]

    assert client.get(f"/products/{product_id}").json()["stock_qty"] == 8

    cancelled = client.post(f"/orders/{order_id}/cancel")
    assert cancelled.status_code == 200, cancelled.text

    assert client.get(f"/products/{product_id}").json()["stock_qty"] == 10
    assert client.get(f"/orders/{order_id}").json()["status"] == "CANCELLED"


def test_cancel_order_twice_does_not_restore_stock_twice(client):
    product_id = add_test_product(client, "TEST-CANCEL-TWICE", 10)

    order = client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 2}]},
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]

    first = client.post(f"/orders/{order_id}/cancel")
    assert first.status_code == 200, first.text

    second = client.post(f"/orders/{order_id}/cancel")
    assert second.status_code == 409, second.text
    assert second.json()["error"] == "order_already_cancelled"

    product = client.get(f"/products/{product_id}")
    assert product.status_code == 200, product.text
    assert product.json()["stock_qty"] == 10


def test_duplicate_sku_is_rejected(client):
    sku = "TEST-DUPLICATE"
    product_id = add_test_product(client, sku, 10)

    before = client.get(f"/products/{product_id}")
    assert before.status_code == 200, before.text

    duplicate = client.post(
        "/products",
        json={"sku": sku, "name": "Other name", "price": "9.00", "stock_qty": 2},
    )
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["error"] == "duplicate_sku"

    after = client.get(f"/products/{product_id}")
    assert after.status_code == 200, after.text
    assert after.json() == before.json()


def test_daily_report_excludes_cancelled_orders(client):
    water = add_test_product(client, "REPORT-WATER", 10)
    cola = add_test_product(client, "REPORT-COLA", 10)
    tea = add_test_product(client, "REPORT-TEA", 10)
    juice = add_test_product(client, "REPORT-JUICE", 10)

    paid = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": water, "quantity": 4},
                {"product_id": cola, "quantity": 3},
                {"product_id": tea, "quantity": 2},
                {"product_id": juice, "quantity": 1},
            ]
        },
    )
    assert paid.status_code == 201, paid.text

    other = client.post(
        "/orders",
        json={"items": [{"product_id": juice, "quantity": 6}]},
    )
    assert other.status_code == 201, other.text
    other_id = other.json()["id"]

    cancelled = client.post(f"/orders/{other_id}/cancel")
    assert cancelled.status_code == 200, cancelled.text

    day = "2026-01-15"
    with closing(database.connect_db()) as db:
        db.execute(
            "UPDATE orders SET created_at = ? WHERE id IN (?, ?)",
            (f"{day} 12:00:00", paid.json()["id"], other_id),
        )
        db.commit()

    response = client.get("/reports/daily-sales", params={"date": day})
    assert response.status_code == 200, response.text

    report = response.json()
    assert report["order_count"] == 1
    assert report["total_revenue"] == "25.00"
    assert [
        (product["product_id"], product["quantity_sold"])
        for product in report["top_products"]
    ] == [(water, 4), (cola, 3), (tea, 2)]
