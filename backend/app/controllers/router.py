from fastapi import APIRouter

from app.controllers.exchange_rates import router as exchange_rates_router
from app.controllers.health import router as health_router
from app.controllers.payments import router as payments_router
from app.controllers.references import router as references_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(exchange_rates_router)
api_router.include_router(references_router)
api_router.include_router(payments_router)
