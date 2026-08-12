import ctypes
from ctypes import wintypes
import logging

logger = logging.getLogger("WinCertStore")

# Constants for Windows Certificate Store
CERT_STORE_PROV_SYSTEM = 10
CERT_SYSTEM_STORE_CURRENT_USER = 1 << 16
CERT_STORE_OPEN_EXISTING_FLAG = 0x00004000
X509_ASN_ENCODING = 0x00000001
PKCS_7_ASN_ENCODING = 0x00010000
PKCS_AND_X509_ENCODING = X509_ASN_ENCODING | PKCS_7_ASN_ENCODING
CERT_STORE_ADD_REPLACE_EXISTING = 3
CERT_FIND_SUBJECT_STR_W = 0x00080007

crypt32 = ctypes.WinDLL('crypt32', use_last_error=True)

# Explicitly define argtypes and restypes for 64-bit compatibility (prevents handle truncation)
crypt32.CertOpenStore.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.c_wchar_p]
crypt32.CertOpenStore.restype = ctypes.c_void_p

crypt32.CertAddEncodedCertificateToStore.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
crypt32.CertAddEncodedCertificateToStore.restype = wintypes.BOOL

crypt32.CertCloseStore.argtypes = [ctypes.c_void_p, wintypes.DWORD]
crypt32.CertCloseStore.restype = wintypes.BOOL

crypt32.CertFindCertificateInStore.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_wchar_p, ctypes.c_void_p]
crypt32.CertFindCertificateInStore.restype = ctypes.c_void_p

crypt32.CertDeleteCertificateFromStore.argtypes = [ctypes.c_void_p]
crypt32.CertDeleteCertificateFromStore.restype = wintypes.BOOL

crypt32.CertFreeCertificateContext.argtypes = [ctypes.c_void_p]
crypt32.CertFreeCertificateContext.restype = wintypes.BOOL

def _open_my_store():
    return crypt32.CertOpenStore(
        ctypes.c_void_p(CERT_STORE_PROV_SYSTEM), 0, None,
        CERT_SYSTEM_STORE_CURRENT_USER | CERT_STORE_OPEN_EXISTING_FLAG,
        "MY"
    )


def _find_in_store(store_handle, subject_name: str):
    p_cert_context = crypt32.CertFindCertificateInStore(
        store_handle, PKCS_AND_X509_ENCODING, 0,
        CERT_FIND_SUBJECT_STR_W,
        subject_name, None
    )
    if not p_cert_context and "CN=" in subject_name:
        cn_part = subject_name.split("CN=")[1].split(",")[0].strip()
        if cn_part:
            logger.debug(f"Full subject match failed. Retrying with CN: {cn_part}")
            p_cert_context = crypt32.CertFindCertificateInStore(
                store_handle, X509_ASN_ENCODING, 0,
                CERT_FIND_SUBJECT_STR_W,
                cn_part, None
            )
    return p_cert_context


class WinCertStore:
    @staticmethod
    def publish_certificate(der_bytes: bytes) -> bool:
        """نشر الشهادة العامة في مخزن الشخصي (MY) للمستخدم الحالي. لا يرمي استثناءات."""
        if not der_bytes:
            logger.warning("Skip publish: empty DER")
            return False
        try:
            logger.debug(f"Publishing certificate to Windows Store (Size: {len(der_bytes)} bytes)...")
            store_handle = _open_my_store()
            if not store_handle:
                logger.warning(f"Failed to open Windows Cert Store: {ctypes.get_last_error()}")
                return False
            try:
                res = crypt32.CertAddEncodedCertificateToStore(
                    store_handle, PKCS_AND_X509_ENCODING,
                    der_bytes, len(der_bytes),
                    CERT_STORE_ADD_REPLACE_EXISTING, None
                )
                if res:
                    logger.info(f"Certificate ({len(der_bytes)} bytes) published to Windows MY store.")
                    return True
                logger.warning(f"Failed to add cert to store: {ctypes.get_last_error()}")
                return False
            finally:
                crypt32.CertCloseStore(store_handle, 0)
        except Exception as e:
            logger.warning(f"WinCertStore publish failed (non-fatal): {e}")
            return False

    @staticmethod
    def remove_certificate(subject_name: str) -> bool:
        """حذف الشهادة من المخزن عند logout أو فصل التوكن. لا يرمي استثناءات."""
        if not subject_name:
            return False
        try:
            logger.debug(f"Attempting to remove certificate with subject: {subject_name}")
            store_handle = _open_my_store()
            if not store_handle:
                logger.warning(f"Failed to open Windows Cert Store for removal: {ctypes.get_last_error()}")
                return False

            p_cert_context = None
            try:
                p_cert_context = _find_in_store(store_handle, subject_name)
                # CertDeleteCertificateFromStore always frees pCertContext.
                if p_cert_context:
                    if crypt32.CertDeleteCertificateFromStore(p_cert_context):
                        logger.info(f"Removed certificate for {subject_name} from Windows MY store.")
                        p_cert_context = None
                        return True
                    logger.warning(f"Failed to delete found certificate: {ctypes.get_last_error()}")
                    return False
                logger.debug(f"Certificate with subject '{subject_name}' not found in Windows Store.")
                return False
            finally:
                crypt32.CertCloseStore(store_handle, 0)
        except Exception as e:
            logger.warning(f"WinCertStore remove failed (non-fatal): {e}")
            return False

    @staticmethod
    def has_certificate(subject_name: str) -> bool:
        """Best-effort presence check for tests and diagnostics."""
        if not subject_name:
            return False
        try:
            store_handle = _open_my_store()
            if not store_handle:
                return False
            p_cert_context = None
            try:
                p_cert_context = _find_in_store(store_handle, subject_name)
                return bool(p_cert_context)
            finally:
                if p_cert_context:
                    crypt32.CertFreeCertificateContext(p_cert_context)
                crypt32.CertCloseStore(store_handle, 0)
        except Exception as e:
            logger.debug(f"WinCertStore has_certificate failed: {e}")
            return False