# Windows Certificate Store (MY)

ESA-Lite publishes the token’s **public** X.509 certificate into the current user’s Personal store (`CURRENT_USER\MY`) so Windows apps (Edge, Chrome, certmgr) can see it. No private key is exported.

## Contract

| Event | Action |
|-------|--------|
| Successful **login** and `certificate_der` is available | `WinCertStore.publish_certificate(der)` |
| **Logout** or **PIN change** (which logs out) | `WinCertStore.remove_certificate(subject)` |
| Token **disconnect** (USB unplug / scan miss) | `WinCertStore.remove_certificate(subject)` if subject is known |

Failures (store locked, access denied, cert not found) are **logged only**. Login, logout, PIN, and the UI must still succeed.

## Privacy / permissions

- Only the public certificate is written to the user store.
- No elevation is required for `CURRENT_USER\MY`.
- Removing the token or logging out removes the published cert (best-effort).

## Verify

After login: `certmgr.msc` → Personal → Certificates, or PowerShell `Get-ChildItem Cert:\CurrentUser\My`.
After logout or unplug: the same subject should be gone (or a warning in the log if Windows refused the delete).
