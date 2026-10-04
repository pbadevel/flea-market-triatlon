class AppError(Exception):
    def __init__(self, message: str):
        super().__init__(message)

        self.message = message


class BadRequest(AppError):
    def __init__(self, message: str = "Bad request"):
        super().__init__(message)


class ResourceNotFound(BadRequest):
    def __init__(self, message: str = "Not found"):
        super().__init__(message)


class Unauthorized(BadRequest):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message)

class ValueRequestError(BadRequest):
    def __init__(self, message: str = "Wrong data"):
        super().__init__(message)


class Forbidden(BadRequest):
    def __init__(self, message: str = "No rights"):
        super().__init__(message)


class Banned(AppError):
    def __init__(self, message: str = "Аккаунт заблокирован"):
        super().__init__(message)



class PhoneVerificationError(ValueError):
    """Ошибка верификации телефона."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "PHONE_VERIFICATION_ERROR",
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class PhoneNotVerifiedError(PhoneVerificationError):
    """Действие требует подтверждённого телефона."""

    def __init__(self, message: str = "Для этого действия нужно подтвердить номер телефона") -> None:
        super().__init__(message, status_code=403, code="PHONE_NOT_VERIFIED")


class SMSDeliveryError(PhoneVerificationError):
    """Ошибка доставки SMS."""

    def __init__(self, message: str = "Не удалось отправить SMS") -> None:
        super().__init__(message, status_code=502, code="SMS_DELIVERY_ERROR")