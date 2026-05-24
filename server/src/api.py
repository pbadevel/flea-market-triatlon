from fastapi import Depends

from src.auth.dependencies import WebAdminAuthenticator
from src.auth.endpoints import router as auth_router
from src.routing import APIRouter
from src.admin.users.admin_endpoints import router as admin_users_router
from src.admin.stats.endpoints import router as admin_stats_router
from src.endpoints.ads import router as ads_router
from src.endpoints.filters import router as filter_router
from src.endpoints.products import router as product_router

router = APIRouter(prefix="/v1")

router.include_router(auth_router)
router.include_router(ads_router)
router.include_router(filter_router)
router.include_router(product_router)

admin_router = APIRouter(prefix="/admin", dependencies=[Depends(WebAdminAuthenticator)])
admin_router.include_router(admin_users_router)
admin_router.include_router(admin_stats_router)

router.include_router(admin_router)
