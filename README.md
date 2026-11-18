# SysPOS Mini POS Orders API

SysPOS is a retail point-of-sale REST API built with FastAPI and SQLite. It manages a product catalog and stock, records and cancels sales, and reports daily revenue and the three best-selling products by quantity.

## Run locally

Use Python 3.12 with SQLite 3.35 or later. From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 database.py
```

Set a local API key in the terminal that will run the server. Generate one if you do not already have one:

```bash
export SYSPOS_API_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
printenv SYSPOS_API_KEY
python3 -m uvicorn main:app --reload
```

Open [Swagger UI](http://127.0.0.1:8000/docs), click **Authorize**, and paste the key value. The product, order, and report endpoints require the `X-API-Key` header. A missing or incorrect key returns `401`. Keep your key out of the repository.

## API endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| `POST` | `/products` | Create a product. A duplicate SKU returns `409`. |
| `GET` | `/products` | List products with `page`, `page_size`, `search`, and `in_stock` query parameters. |
| `GET` | `/products/{product_id}` | Return one product, or `404` if it is missing. |
| `PATCH` | `/products/{product_id}` | Update the name, price, or active status. The SKU is immutable. |
| `POST` | `/products/{product_id}/stock-adjustments` | Apply a signed `delta` with a `reason`. A negative resulting stock returns `400`. |
| `POST` | `/orders` | Create a paid order, capture the unit prices, and reduce stock. |
| `GET` | `/orders/{order_id}` | Return an order with its items and original sale prices. |
| `POST` | `/orders/{order_id}/cancel` | Cancel the order and restore stock once. Repeating the cancellation returns `409`. |
| `GET` | `/reports/daily-sales?date=YYYY-MM-DD` | Return the order count, revenue, and top three products by quantity sold. |

### Quick Swagger demo

1. Create a product with `POST /products`. Use a fresh SKU if you repeat the demo.

   ```json
   {"sku": "WATER-01", "name": "Water", "price": "2.50", "stock_qty": 10}
   ```

2. Create an order with `POST /orders`. Replace `1` with the product ID returned in step 1.

   ```json
   {"items": [{"product_id": 1, "quantity": 2}]}
   ```

3. Use the returned **order ID** with `GET /orders/{order_id}`. The order total is `5.00`. Use `GET /products/{product_id}` to see the remaining stock of `8`.
4. Run the daily report using the date from the order's `created_at` field. Then call `POST /orders/{order_id}/cancel` and run the report again. The cancelled order is excluded and the product's stock returns to `10` if no other stock changes were made.

## Run the tests

With the virtual environment active:

```bash
python3 -m pytest -q
```

The tests use FastAPI's `TestClient` and a temporary SQLite database for each test. They cover stock reduction on a successful order, rejection without changes when stock is insufficient, stock restoration on cancellation, repeat cancellation, duplicate SKUs, and daily reporting that excludes cancelled orders.

## Run with Docker

Export `SYSPOS_API_KEY` in the terminal that launches the container, then run:

```bash
docker build -t syspos .
docker run --rm -p 127.0.0.1:8001:8000 -e SYSPOS_API_KEY -v syspos-data:/data syspos
```

Open [Swagger UI for Docker](http://127.0.0.1:8001/docs) and authorize with the same key. The container initializes SQLite on startup. The `syspos-data` volume keeps products and orders when the container is replaced.

## Design decisions

- The API uses `Decimal` for money. SQLite stores amounts as integer cents, and the API returns decimal amounts as JSON strings.
- Order creation checks that products exist, are active, and have enough stock. The order, its price snapshots, and the stock changes are committed in a single transaction. Repeated product IDs in one request are combined into one order item.
- Orders start as `PAID`. Cancellation changes their status to `CANCELLED` and restores the original quantities in a single transaction.
- Daily reports use UTC dates and exclude cancelled orders from all metrics.
- Stock adjustments require a reason. The current schema stores the resulting stock quantity.

## What I would improve with more time

- Add a pending payment state. Mark an order as paid once payment is confirmed.
- Track preparation separately from payment. When a customer cancels, restore only items that can still be sold and record prepared or damaged items as waste.

