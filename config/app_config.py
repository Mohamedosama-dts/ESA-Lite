import platform
import os

class AppConfig:
    def __init__(self):
        # Agent Identity
        self.MACHINE_NAME = platform.node()
        self.AGENT_VERSION = "2.1.1"
        self.AGENT_PREFIX = "ESA"
        self.AGENT_FULL_NAME = "Electronic Signature Agent – Lite"

        # Live DLL scan list lives in ConfigLoader.known_drivers (not here).
        # Deprecated mirror for external readers only — HealthCheck ignores this.
        self.TARGET_DLLS = ["eps2003csp11.dll", "entersafe_p11.dll", "wdpkcs.dll"]
