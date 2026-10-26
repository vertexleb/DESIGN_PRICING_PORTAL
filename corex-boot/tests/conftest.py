import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

GB = 1000**3


def raw_disk(number, name="SanDisk Ultra", size=16 * GB, bus="USB", uid=None, serial=None, letters=("E",),
             boot=False, system=False, readonly=False):
    return {
        "Number": number, "FriendlyName": name, "SerialNumber": serial or f"SN{number}",
        "UniqueId": uid if uid is not None else f"USBSTOR\\DISK&VEN_{number}", "Size": size,
        "BusType": bus, "IsBoot": boot, "IsSystem": system, "IsOffline": False, "IsReadOnly": readonly,
        "PartitionStyle": "MBR", "Location": "", "DriveLetters": list(letters),
    }


NVME = dict(name="Samsung SSD 980 PRO 1TB", size=1000 * GB, bus="NVMe", letters=("C",), boot=True, system=True)


def snapshot_json(*disks, system_drive="C", page_files=("C",)):
    return {"SystemDrive": system_drive, "PageFileDrives": list(page_files), "Disks": list(disks)}


@pytest.fixture
def tmp_cache(tmp_path):
    d = tmp_path / "cache"
    d.mkdir()
    return d
