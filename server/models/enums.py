import enum

class AdStatus(enum.StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    sold = "sold"
    removed = "removed"
    unpublished = "unpublished"
    paused = "paused"

class AdCondition(enum.StrEnum):
    new = "Новое"
    excellent = "Отличное"
    good = "Хорошее"
    used = "Есть следы использования"
    unknown = "Не указано"
    
class Category(enum.StrEnum):
    swim = "swim"
    bike = "bike"
    run = "run"
    electronics = "electronics"
    slots = "slots"

class ContactMethod(enum.StrEnum):
    telegram = "telegram"
    phone = "phone"

class AdType(enum.StrEnum):
    sale = "Продажа"
    rent = "Аренда"