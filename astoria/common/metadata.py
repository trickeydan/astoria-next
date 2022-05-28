"""Schema for the robot metadata."""
import platform
import re
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel

from astoria import __version__
from astoria.common.config import AstoriaConfig


class RobotMode(Enum):
    """Running Status of the manager daemon."""

    COMP = "COMP"
    DEV = "DEV"


class Metadata(BaseModel):
    """Astoria Metadata."""

    class Config:
        """Pydantic config."""

        validate_assignment = True

    @classmethod
    def init(cls, config: AstoriaConfig) -> 'Metadata':
        """
        Initialise the metadata and populate with data.

        Based on information from software and the astoria configuration.
        """
        uname = platform.uname()
        os_release = cls.get_os_version_info()
        return cls(
            astoria_version=__version__,
            kernel_version=uname.release,
            arch=uname.machine,
            python_version=platform.python_version(),
            libc_ver="".join(platform.libc_ver()),
            usercode_entrypoint=config.astprocd.default_usercode_entrypoint,
            os_name=os_release['NAME'],
            os_pretty_name=os_release['PRETTY_NAME'],
            os_version=os_release['VERSION_ID'],
        )

    @classmethod
    def get_os_version_info(cls) -> Dict[str, str]:
        """
        Reads OS version information from /etc/os-release.

        See man page os-release(5) for more information.
        :return: dict OS release values
        """
        os_release_path = Path('/etc/os-release')
        if os_release_path.exists():
            return {
                k: v for k, v in
                re.findall(r'^([A-Z_]+)="?([^"]+)"?$', os_release_path.read_text(), flags=re.MULTILINE)
            }

        return {}

    def is_wifi_valid(self) -> bool:
        """
        Check if the WiFi configuration is valid to be turned on.

        Checks that the WiFi is enabled and that the config params are set.Optional
        :return: boolean indicating whether the WiFi can be turned on.
        """
        return all([
            self.wifi_enabled,
            self.wifi_ssid is not None,
            self.wifi_psk is not None,
            self.wifi_region is not None,
        ])

    # From Meta USB
    arena: str = "A"
    zone: int = 0
    mode: RobotMode = RobotMode.DEV
    marker_offset: int = 0
    game_timeout: Optional[int] = None
    wifi_enabled: bool = True

    # From Software
    astoria_version: str
    kernel_version: str
    arch: str
    python_version: str
    libc_ver: str
    os_name: Optional[str] = None
    os_pretty_name: Optional[str] = None
    os_version: Optional[str] = None

    # From robot settings file
    usercode_entrypoint: str
    wifi_ssid: Optional[str] = None
    wifi_psk: Optional[str] = None
    wifi_region: Optional[str] = None
