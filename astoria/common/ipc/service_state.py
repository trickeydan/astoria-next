"""Manager Messages."""
from enum import Enum
from pathlib import Path
from typing import Dict, Generic, Optional, TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel

from astoria.common.code_status import CodeStatus
from astoria.common.disks import DiskInfo, DiskTypeCalculator, DiskUUID
from astoria.common.metadata import Metadata

StateT = TypeVar('StateT', bound=BaseModel)


class ServiceStatus(Enum):
    """Running Status of the manager daemon."""

    STOPPED = "STOPPED"
    RUNNING = "RUNNING"


class ServiceMessage(GenericModel, Generic[StateT]):
    """Common data that all manager messages output."""

    status: ServiceStatus
    state: Optional[StateT]


class ProcessState(BaseModel):
    """
    Status message for Process Manager.

    Published to astoria/astprocd
    """

    code_status: Optional[CodeStatus]
    disk_info: Optional[DiskInfo]


class MetadataState(BaseModel):
    """
    Status message for Metadata Manager.

    Published to /astoria/astmetad
    """

    metadata: Metadata


class DiskState(BaseModel):
    """
    Status message for Disk Manager.

    Published to /astoria/astdiskd
    """

    disks: Dict[DiskUUID, Path]

    def calculate_disk_info(
        self,
        default_usercode_entrypoint: str,
    ) -> Dict[DiskUUID, DiskInfo]:
        """
        Calculate the disk info of the disks in the message.

        As astdiskd only gives us information about the path of each disk,
        we need to calculate the type of each disk in the message.

        :param default_usercode_entrypoint: default entrypoint from astoria config
        :returns: A dictionary of disk UUIDs and disk information.
        """
        disk_type_calculator = DiskTypeCalculator(default_usercode_entrypoint)
        return {
            uuid: DiskInfo(
                uuid=uuid,
                mount_path=path,
                disk_type=disk_type_calculator.calculate(path),
            )
            for uuid, path in self.disks.items()
        }


class WiFiState(BaseModel):
    """
    Status message for WiFi Manager.

    Published to /astoria/astwifid
    """

    hotspot_running: bool
