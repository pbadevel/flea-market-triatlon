from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from src.kit.openapi import APITag
from src.auth.dependencies import WebUser, WebAdmin
from src.kit.pagination import ListResource, PaginationParamsQuery
from src.postgres import get_db_session
from src.routing import APIRouter
from src.admin.stats.scheme import AdminInfoScheme, AdminAlertsInfo, AdminRevenueInfo, AdminUserInfo
from src.exceptions import ValueRequestError
from src.services.user import user_service

from src.logging import get_logger




log = get_logger()

router = APIRouter(
    prefix="/stats",
    tags=["Stats", APITag.private],
)



# @router.get("", description="Admin list users")
# async def get_users(
#     user: WebAdmin,
#     session: AsyncSession = Depends(get_db_session)
# ) -> AdminInfoScheme:


#     subscription_repo = subscription_service.get_repository(session)
#     active_count_stmt = subscription_repo.get_count_stmt_base().where(Subscription.status == UserSubscriptionStatus.ACTIVE)
#     expired_count_stmt = subscription_repo.get_count_stmt_base().where(Subscription.status == UserSubscriptionStatus.EXPIRED)
#     new_count_stmt = subscription_repo.get_count_stmt_base().where(Subscription.status == UserSubscriptionStatus.NEW)

#     users = AdminUserInfo(
#         total = await user_service.get_users_count(session),
#         active = await subscription_repo.count_base(stmt=active_count_stmt),
#         trial = await subscription_repo.count_base(stmt=new_count_stmt),
#         expired = await subscription_repo.count_base(stmt=expired_count_stmt),
#     )

#     receipt_repo = receipt_service.get_repository(session)
#     rub_sum = receipt_repo.get_count_stmt_base().where(Receipt.method == PaymentMethods.SBP)
#     cb_sum = receipt_repo.get_count_stmt_base().where(Receipt.method == PaymentMethods.CB)
#     stars_sum = receipt_repo.get_count_stmt_base().where(Receipt.method == PaymentMethods.STARS)

#     revenue = AdminRevenueInfo(
#         rub=await receipt_repo.count_base(rub_sum),
#         crypto=await receipt_repo.count_base(cb_sum),
#         stars=await receipt_repo.count_base(stars_sum)
#     )





#     return AdminInfoScheme(
#         users=users,
#         revenue=revenue,
#         # alerts=AdminAlertsInfo(
#         #     expiring_today=0,

        
#         #     failed_payments=0,
#         #     technical_errors=0
#         # )
#     )


