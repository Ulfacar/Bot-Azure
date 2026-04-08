from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.messages import router as messages_router
from app.api.routes.operators import router as operators_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.exely import router as exely_router
from app.api.routes.notes import router as notes_router
from app.api.routes.admin import router as admin_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(conversations_router)
api_router.include_router(messages_router)
api_router.include_router(operators_router)
api_router.include_router(knowledge_router)
api_router.include_router(exely_router)
api_router.include_router(notes_router)
api_router.include_router(admin_router)
