from fastapi import FastAPI
from products import router as products_router
from orders import router as orders_router
from reports import router as reports_router

app= FastAPI(title="SysPOS Mini POS Orders API")


app.include_router(products_router)
app.include_router(orders_router)
app.include_router(reports_router)