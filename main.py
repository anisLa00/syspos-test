from fastapi import FastAPI
from products import router as products_router

app= FastAPI(title="SysPOS Mini POS Orders API")


app.include_router(products_router)