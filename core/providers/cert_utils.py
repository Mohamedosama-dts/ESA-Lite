# providers/cert_utils.py
import logging
from typing import Optional
import re
import warnings
logger = logging.getLogger("CertUtils")
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization, hashes
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    logger.error("Cryptography library or its binary dependencies missing. Certificate parsing will fail.", exc_info=True)



class CertUtils:
    @staticmethod
    def parse_der_certificate(der_bytes: bytes) -> Optional[dict]:
        """
        Parses a DER-encoded X.509 certificate and extracts relevant information.
        Returns a dictionary of certificate details or None if parsing fails.
        """
        if not der_bytes:
            return None

        if not _CRYPTO_AVAILABLE:
            logger.warning("Cryptography library not available. Cannot perform full certificate parsing.")
            # Fallback to basic CN extraction if cryptography is not available
            cn = CertUtils._parse_subject_dn_fallback(der_bytes)
            if cn:
                return {
                    'cert_label': cn,
                    'token_type': "E-Signature", # Default fallback type
                    'certificate_der': der_bytes.hex(),
                }
            return None

        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always") # تأكد من التقاط جميع التحذيرات
                
                cert_obj = x509.load_der_x509_certificate(der_bytes, default_backend())
                
                # تسجيل أي تحذيرات تم التقاطها
                for warning_message in w:
                    logger.warning(f"Cryptography warning during cert parsing: {warning_message.message}")

                cert_data = {}

                cert_data['certificate_subject'] = cert_obj.subject.rfc4514_string() # نتركه كاملاً للمنطق الداخلي
                cert_data['certificate_issuer'] = CertUtils._get_common_name(cert_obj.issuer)

                cert_data['token_type'] = "E-Seal" if "VATEG-" in cert_data['certificate_subject'] else "E-Signature"
                cert_data['vat_eg'] = CertUtils._extract_vat_eg_from_subject(cert_data['certificate_subject'])
                cert_data['certificate_expiry'] = cert_obj.not_valid_after_utc.isoformat() + "Z"

                cn_list = cert_obj.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
                if cn_list:
                    cert_data['cert_label'] = cn_list[0].value
                else:
                    cert_data['cert_label'] = "Unknown"

                pub_key = cert_obj.public_key()
                pem = pub_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                cert_data['certificate_public_key'] = pem.decode('utf-8')

                digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
                digest.update(der_bytes)
                cert_data['certificate_hash_v2'] = digest.finalize().hex()

                cert_data['certificate_der'] = der_bytes.hex()

                return cert_data
        except Exception as e:
            logger.error(f"Failed to parse DER certificate with cryptography: {e}")
            # Fallback to basic CN extraction if cryptography parsing fails
            cn = CertUtils._parse_subject_dn_fallback(der_bytes)
            if cn:
                return {
                    'cert_label': cn,
                    'token_type': "E-Signature", # Default fallback type
                    'certificate_der': der_bytes.hex(),
                    'vat_eg': None
                }
            return None

    @staticmethod
    def _parse_subject_dn_fallback(subject_bytes: bytes) -> Optional[str]:
        """
        Fallback method to extract CN from Subject DN (DER Encoded) if cryptography fails.
        Searches for OID 2.5.4.3 (commonName) -> 06 03 55 04 03
        """
        try:
            # This is a simplified and less robust parsing than full X.509
            # It's primarily for cases where cryptography is not available or fails.
            # OID for commonName: 2.5.4.3
            oid_cn = b'\x06\x03\x55\x04\x03'
            
            idx = subject_bytes.find(oid_cn)
            if idx != -1:
                # Skip OID (5 bytes)
                curr = idx + 5
                if curr >= len(subject_bytes): return None
                
                # Tag (skip)
                curr += 1
                
                # Length
                if curr >= len(subject_bytes): return None
                length = subject_bytes[curr]
                curr += 1
                
                if length & 0x80:
                    n_bytes = length & 0x7F
                    if curr + n_bytes > len(subject_bytes): return None
                    length = int.from_bytes(subject_bytes[curr:curr+n_bytes], 'big')
                    curr += n_bytes
                
                if curr + length > len(subject_bytes): return None
                
                value_bytes = subject_bytes[curr:curr+length]
                return value_bytes.decode('utf-8', errors='replace')
        except Exception as e:
            logger.debug(f"Fallback DN parsing failed: {e}")
        return None
    
    @staticmethod
    def _extract_vat_eg_from_subject(subject: str) -> Optional[str]:
        """
        Extract VAT-EG number from the subject string if present.
        Looks for patterns like "VATEG-123456789" and returns the numeric part.
        """
        if not subject:
            return None
        
        # البحث عن VATEG- متبوعاً بأرقام بشكل أكثر مرونة
        match = re.search(r'VATEG-(\d+)', subject)
        if match:
            return match.group(1)
            
        # محاولة أخيرة في حالة كان التنسيق مختلفاً (Split)
        for part in [p.strip() for p in subject.split(',')]:
            if part.startswith("VATEG-"):
                return part.replace("VATEG-", "").strip()
                
        return None

    @staticmethod
    def _get_common_name(name_obj) -> str:
        """
        Extracts the Common Name (CN) from an X.509 Name object.
        Falls back to the full RFC4514 string if CN is missing.
        """
        try:
            cn_list = name_obj.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
            if cn_list:
                return cn_list[0].value
        except Exception: pass
        return name_obj.rfc4514_string()