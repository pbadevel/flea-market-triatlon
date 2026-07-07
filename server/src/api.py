from fastapi import Depends

from src.auth.dependencies import WebAdminAuthenticator
from src.routing import APIRouter

from src.endpoints.client.ads import router as ads_router
from src.endpoints.client.filters import router as filter_router
from src.endpoints.client.products import router as product_router
from src.endpoints.client.reviews import router as reviews_router
from src.endpoints.client.bot_test import router as test_bot_router
from src.endpoints.client.profile import router as profile_router
from src.endpoints.client.notifications import router as notifications_router

from src.endpoints.admin.moderators import router as admin_moderator_router
from src.endpoints.admin.categories import router as admin_categories_router
from src.endpoints.admin.users import router as admin_users_router
from src.endpoints.admin.notifications import router as admin_notifications_router

from src.auth.auth_email import router as email_auth_router
from src.auth.auth_telegram import router as tg_auth_router

from src.auth.auth_test import router as auth_test_router
from src.endpoints.client.test_tg_message import router as test_tg_message_router


router = APIRouter(prefix="/v1")


# CLIENT ROUTERS
router.include_router(profile_router)
router.include_router(ads_router)
router.include_router(filter_router)
router.include_router(product_router)
router.include_router(reviews_router)
router.include_router(notifications_router)

# ADMIN ROUTERS
router.include_router(admin_moderator_router)
router.include_router(admin_categories_router)
router.include_router(admin_users_router)

# AUTH ROUTERS
router.include_router(email_auth_router)
router.include_router(tg_auth_router)

# TEST ROUTERS (COMMENT WHEN PRODUCTION!!!)
router.include_router(test_bot_router)
router.include_router(auth_test_router)
router.include_router(test_tg_message_router)

admin_router = APIRouter(prefix="/admin", dependencies=[Depends(WebAdminAuthenticator)])
admin_router.include_router(admin_notifications_router)



router.include_router(admin_router)
