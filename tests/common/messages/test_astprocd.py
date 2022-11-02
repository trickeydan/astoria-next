"""Tests for astprocd message definitions."""
from pathlib import Path

from astoria.common.code_status import CodeStatus
from astoria.common.disks import DiskInfo, DiskType, DiskUUID
from astoria.common.ipc import ProcessState, ServiceStatus


def test_proc_manager_fields() -> None:
    """Test that the fields on the status message work."""
    info = DiskInfo(
        uuid=DiskUUID("foobar"),
        mount_path=Path("/mnt"),
        disk_type=DiskType.NOACTION,
    )

    pmm = ProcessState(
        disk_info=info,
        code_status=CodeStatus.RUNNING,
        status=ServiceStatus.RUNNING,
    )

    assert pmm.json() == '{"code_status": "code_running", "disk_info": {"uuid": "foobar", "mount_path": "/mnt", "disk_type": "NOACTION"}}'  # noqa: E501
