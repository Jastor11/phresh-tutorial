from fastapi import APIRouter

from app.api.routes.cleanings import router as cleanings_router
from app.api.routes.users import router as users_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.offers import router as offers_router


router = APIRouter()


router.include_router(cleanings_router, prefix="/cleanings", tags=["cleanings"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
router.include_router(offers_router, prefix="/cleanings/{cleaning_id}/offers", tags=["offers"])
