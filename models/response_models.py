from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Union
from .enums import ErrorCode

class OperationResult(BaseModel):
    """
    العقد الموحد لردود الأفعال (Success/Failure Contract).
    يضمن استلام الواجهة الرسومية لهيكل ثابت دائماً.
    """
    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(..., description="حالة نجاح العملية")
    message: str = Field(..., description="رسالة توضيحية للمستخدم")
    data: Optional[Any] = Field(None, description="البيانات الناتجة في حالة النجاح")
    error_code: Optional[ErrorCode] = Field(None, description="كود الخطأ المعياري في حالة الفشل")

    @classmethod
    def failure(cls, message: str, error_code: ErrorCode, data: Any = None):
        return cls(success=False, message=message, error_code=error_code, data=data)

    @classmethod
    def success_res(cls, message: str, data: Any = None):
        return cls(success=True, message=message, data=data)