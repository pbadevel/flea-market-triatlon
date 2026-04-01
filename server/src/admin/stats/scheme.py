from src.kit.schemas import Schema


class AdminAlertsInfo(Schema):
    expiring_today: int
    failed_payments: int
    technical_errors: int

class AdminRevenueInfo(Schema):
    rub: int
    crypto: int
    stars: int

class AdminUserInfo(Schema):
    total: int
    active: int
    trial: int
    expired: int


class AdminInfoScheme(Schema):
    users: AdminUserInfo
    revenue: AdminRevenueInfo
    # alerts: AdminAlertsInfo
