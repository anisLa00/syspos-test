from fastapi import Depends, FastAPI

from auth import APIKeyError, api_key_error_response, require_api_key
from orders import router as orders_router
from products import router as products_router
from reports import router as reports_router

app = FastAPI(title="SysPOS Mini POS Orders API")


app.add_exception_handler(APIKeyError, api_key_error_response)

protected = [Depends(require_api_key)]

app.include_router(products_router, dependencies=protected)
app.include_router(orders_router, dependencies=protected)
app.include_router(reports_router, dependencies=protected)
