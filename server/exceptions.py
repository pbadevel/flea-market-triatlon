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
