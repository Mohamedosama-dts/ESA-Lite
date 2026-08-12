# Bundled PKCS#11 fallbacks

Place **x64** DLLs that ESA-Lite is allowed to redistribute under `x64/`.

Current policy:

- **Allowed:** ePass / EnterSafe family (`eps2003csp11.dll`, optional `entersafe_p11.dll`).
- **Not allowed:** WatchData `wdpkcs.dll` — users must install PROXKey CSP. Health check will warn if it is missing.
