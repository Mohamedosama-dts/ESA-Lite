from .enums import ErrorCode

class BaseTokenError(Exception):
    def __init__(self, message: str, code: ErrorCode):
        super().__init__(message)
        self.code = code

class TokenNotFoundError(BaseTokenError):
    def __init__(self, serial: str):
        super().__init__(f"Token with serial {serial} not found", ErrorCode.TOKEN_NOT_FOUND)

class AuthError(BaseTokenError):
    def __init__(self, message: str, code: ErrorCode = ErrorCode.PIN_INVALID):
        super().__init__(message, code)

class HardwareError(BaseTokenError):
    def __init__(self, message: str):
        super().__init__(message, ErrorCode.HARDWARE_FAILURE)

class StrategyError(BaseTokenError):
    def __init__(self, message: str):
        super().__init__(message, ErrorCode.STRATEGY_NOT_READY)