import ctypes
from ctypes import wintypes
import logging
import winreg

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
CERT_KEY_PROV_INFO_PROP_ID = 2

# CryptFindCertificateKeyProvInfo flags (wincrypt.h)
CRYPT_FIND_USER_KEYSET_FLAG = 0x00000001
CRYPT_FIND_SILENT_KEYSET_FLAG = 0x00000040

# CSP name registered by the ESA-Lite MSI for ePass / EnterSafe (Windows CryptoAPI / ITIDA).
ENTERSAFE_CSP_NAME = "EnterSafe ePass2003 CSP v1.0"
_ENTERSAFE_CSP_REG = (
    r"SOFTWARE\Microsoft\Cryptography\Defaults\Provider\EnterSafe ePass2003 CSP v1.0"
)

crypt32 = ctypes.WinDLL('crypt32', use_last_error=True)

# Explicitly define argtypes and restypes for 64-bit compatibility (prevents handle truncation)
crypt32.CertOpenStore.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.c_wchar_p]
crypt32.CertOpenStore.restype = ctypes.c_void_p

crypt32.CertAddEncodedCertificateToStore.argtypes = [
    ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
    ctypes.POINTER(ctypes.c_void_p),
]
crypt32.CertAddEncodedCertificateToStore.restype = wintypes.BOOL

crypt32.CertCloseStore.argtypes = [ctypes.c_void_p, wintypes.DWORD]
crypt32.CertCloseStore.restype = wintypes.BOOL

crypt32.CertFindCertificateInStore.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_wchar_p, ctypes.c_void_p]
crypt32.CertFindCertificateInStore.restype = ctypes.c_void_p

crypt32.CertDeleteCertificateFromStore.argtypes = [ctypes.c_void_p]
crypt32.CertDeleteCertificateFromStore.restype = wintypes.BOOL

crypt32.CertFreeCertificateContext.argtypes = [ctypes.c_void_p]
crypt32.CertFreeCertificateContext.restype = wintypes.BOOL

crypt32.CryptFindCertificateKeyProvInfo.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
crypt32.CryptFindCertificateKeyProvInfo.restype = wintypes.BOOL

crypt32.CertGetCertificateContextProperty.argtypes = [
    ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD),
]
crypt32.CertGetCertificateContextProperty.restype = wintypes.BOOL


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


def _has_key_prov_info(p_cert_context) -> bool:
    """True if CERT_KEY_PROV_INFO_PROP_ID is set on the context."""
    cb = wintypes.DWORD(0)
    # Size probe first
    if not crypt32.CertGetCertificateContextProperty(
        p_cert_context, CERT_KEY_PROV_INFO_PROP_ID, None, ctypes.byref(cb)
    ):
        return False
    return cb.value > 0


def _provider_key_exists(subkey: str) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey, 0, winreg.KEY_READ):
            return True
    except OSError:
        return False


def _entersafe_csp_registered() -> bool:
    """Native (64-bit) view: ESA-Lite MSI registers EnterSafe here for CryptoAPI link."""
    return _provider_key_exists(_ENTERSAFE_CSP_REG)


def _link_private_key_provider(p_cert_context) -> bool:
    """
    Associate the published public cert with a CSP/KSP container that holds
    the matching private key on the smart card (no key export).
    Silent + user keyset only — never prompts for PIN during login publish.

    Failures must never undo a successful CertAdd (ITIDA still needs the MY
    entry; HasPrivateKey may stay False until CSP is registered).
    """
    if not p_cert_context:
        return False
    try:
        if _has_key_prov_info(p_cert_context):
            logger.info("Certificate already linked to a key provider.")
            return True

        # Skip CryptFind when EnterSafe CSP is absent — avoids AV / hard faults
        # on some ePass stacks when only PKCS#11 assets fallback is present.
        if not _entersafe_csp_registered():
            logger.warning(
                "Certificate published to MY without a private-key link "
                "(EnterSafe CSP not registered). "
                "ITIDA Web Signer only lists HasPrivateKey=True certs and has no "
                "PKCS#11 assets fallback — install ESA-Lite (MSI registers "
                "%s + Calais) or another vendor CSP/KSP, keep the token plugged in, "
                "then log in again.",
                ENTERSAFE_CSP_NAME,
            )
            return False

        flags = CRYPT_FIND_USER_KEYSET_FLAG | CRYPT_FIND_SILENT_KEYSET_FLAG
        if crypt32.CryptFindCertificateKeyProvInfo(p_cert_context, flags, None):
            if _has_key_prov_info(p_cert_context):
                logger.info(
                    "Certificate linked to smart-card key provider "
                    "(HasPrivateKey expected True)."
                )
                return True
            logger.warning(
                "CryptFindCertificateKeyProvInfo succeeded but KEY_PROV_INFO "
                "property missing."
            )
            return False

        err = ctypes.get_last_error()
        logger.warning(
            "Certificate is in MY without a private-key link "
            "(CryptFindCertificateKeyProvInfo failed, WinError %s). "
            "ITIDA Web Signer and similar tools only list HasPrivateKey=True certs. "
            "Ensure the token CSP/KSP is registered (ESA-Lite MSI for ePass) and "
            "the token is plugged in, then log in again.",
            err,
        )
        return False
    except OSError as e:
        logger.warning(
            "Key-provider link skipped (OS error, non-fatal): %s. "
            "Public cert remains in MY; HasPrivateKey may be False for ITIDA.",
            e,
        )
        return False
    except Exception as e:
        logger.warning(
            "Key-provider link skipped (%s, non-fatal): %s. "
            "Public cert remains in MY; HasPrivateKey may be False for ITIDA.",
            type(e).__name__,
            e,
        )
        return False


class WinCertStore:
    @staticmethod
    def publish_certificate(der_bytes: bytes) -> bool:
        """نشر الشهادة العامة في MY وربطها بمزوّد مفتاح البطاقة إن وُجد. لا يرمي استثناءات."""
        if not der_bytes:
            logger.warning("Skip publish: empty DER")
            return False
        try:
            logger.debug(f"Publishing certificate to Windows Store (Size: {len(der_bytes)} bytes)...")
            store_handle = _open_my_store()
            if not store_handle:
                logger.warning(f"Failed to open Windows Cert Store: {ctypes.get_last_error()}")
                return False

            p_cert_context = ctypes.c_void_p()
            try:
                # Keep a contiguous buffer; ctypes needs a stable pointer into the encoded blob.
                encoded = (ctypes.c_ubyte * len(der_bytes)).from_buffer_copy(der_bytes)
                res = crypt32.CertAddEncodedCertificateToStore(
                    store_handle, PKCS_AND_X509_ENCODING,
                    encoded, len(der_bytes),
                    CERT_STORE_ADD_REPLACE_EXISTING,
                    ctypes.byref(p_cert_context),
                )
                if not res:
                    logger.warning(f"Failed to add cert to store: {ctypes.get_last_error()}")
                    return False

                logger.info(f"Certificate ({len(der_bytes)} bytes) published to Windows MY store.")
                # Link is best-effort; never treat link failure as publish failure.
                _link_private_key_provider(p_cert_context)
                return True
            finally:
                if p_cert_context:
                    crypt32.CertFreeCertificateContext(p_cert_context)
                    p_cert_context = None
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
