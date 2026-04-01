from fastapi import Depends

from src.auth.dependencies import WebAdminAuthenticator
from src.auth.endpoints import router as auth_router
from src.routing import APIRouter
from src.admin.users.admin_endpoints import router as admin_users_router
from src.admin.stats.endpoints import router as admin_stats_router
from src.users.endpoints import router as users_router
from src.controllers.endpoints import router as controller_router
from src.student_cards.endpoints import router as stud_card_router

router = APIRouter(prefix="/v1")

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(controller_router)
router.include_router(stud_card_router)

admin_router = APIRouter(prefix="/admin", dependencies=[Depends(WebAdminAuthenticator)])
admin_router.include_router(admin_users_router)
admin_router.include_router(admin_stats_router)

router.include_router(admin_router)
