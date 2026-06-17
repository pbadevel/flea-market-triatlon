from enum import StrEnum, IntEnum


class UserRole(StrEnum):
    USER = "USER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"

class MediaFor(StrEnum):
    EVENT = "EVENT"
    ACTION = "ACTION"

class AdType(StrEnum):
    rent = "rent"
    sale = "sale"

class QrType(StrEnum):
    event='event'
    action='action'
    student_card='student_card'

class MediaType(StrEnum):
    """
    Photo or etc ...
    """

    PHOTO = "PHOTO"
    # TODO: maybe to add videos ...