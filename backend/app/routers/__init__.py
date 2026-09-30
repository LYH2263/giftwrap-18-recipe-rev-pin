from fastapi import APIRouter
from app.routers import boxes, estimates, history_router, papers, recipes, settings
api_router = APIRouter(prefix="/api")
api_router.include_router(boxes.router)
api_router.include_router(papers.router)
api_router.include_router(recipes.router)
api_router.include_router(estimates.router)
api_router.include_router(history_router.router)
api_router.include_router(settings.router)
