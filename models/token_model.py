from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from .enums import ScanMethod, TokenType

class TokenData(BaseModel):
    """
    نموذج بيانات التوكن الموحد (Strict Model).
    يجمع بين البيانات التشغيلية للوكيل وبين هيكلة قاعدة البيانات CMP_Tokens.
    """
    # 1. Operational Data (Agent Specific)
    model_config = ConfigDict(from_attributes=True)
    slot: str = Field(..., description="Internal Slot ID used by Driver")
    method: ScanMethod = Field(ScanMethod.UNKNOWN, description="Driver method: native or cli")
    logged_in: bool = Field(False, description="Is PIN cached in memory?")
    pin: Optional[str] = Field(None, exclude=True, description="Session PIN (RAM Only)")
    dll_path: Optional[str] = Field(None, description="Absolute PKCS#11 DLL path that owns this token")

    # 2. Identification (Matches CMP_Tokens)
    serial: str = Field(..., description="Physical Serial Number (token_serial_number)")
    label: str = Field(..., description="Token Friendly Name (token_label)")
    manufacturer: str = Field("Unknown", description="Hardware Manufacturer")
    model: str = Field("Unknown", description="Hardware Model")
    token_type: TokenType = Field(TokenType.SIGNATURE, description="E-Seal or E-Signature")
    vat_eg: Optional[str] = Field(None, description="VAT Registration Number")
    # 3. Certificate Details (Populated ONLY after PIN Entry)
    certificate_issuer: Optional[str] = Field(None, description="Issuer DN")
    certificate_subject: Optional[str] = Field(None, description="Subject DN")
    certificate_expiry: Optional[datetime] = Field(None, description="Expiration Date")
    certificate_hash_v2: Optional[str] = Field(None, description="ESS Signing Cert V2 Hash (SHA256)")
    certificate_der: Optional[str] = Field(None, exclude=True, description="Raw certificate in DER format (Hex)")
    certificate_public_key: Optional[str] = Field(None, description="Base64 Encoded Public Key")
    cert_label: Optional[str] = Field(None, description="Display Name (CN) extracted from certificate")
    last_connected_at: datetime = Field(default_factory=datetime.now)
