"""ISO validation (real ISO built with pycdlib), checksum checks and boot-sector parsing."""

import hashlib
import io

import pytest
from helpers import ISO_FILES, good_mbr, good_pbr

from corex_boot import config
from corex_boot.boot_verify import FileEntry, analyse_layout, mbr_problems, parse_mbr, pbr_info
from corex_boot.errors import ChecksumMismatchError, InvalidIsoError
from corex_boot.iso_verify import check_iso_structure, hash_file, verify_checksum
from corex_boot.usb_copy import copy_tree, list_tree, verify_tree
from corex_boot.errors import UsbWriteError


def build_iso(path):
    pycdlib = pytest.importorskip("pycdlib")
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, udf="2.60")
    dirs = set()
    for rel, data in ISO_FILES.items():
        parts = rel.split("/")
        for i in range(1, len(parts)):
            d = "/".join(parts[:i])
            if d not in dirs:
                dirs.add(d)
                iso.add_directory(iso_path="/" + d.upper()[:8], joliet_path="/" + d, udf_path="/" + d) if i == 1 else \
                    iso.add_directory(iso_path="/" + "/".join(p.upper()[:8] for p in parts[:i]),
                                      joliet_path="/" + d, udf_path="/" + d)
        iso_name = "/" + "/".join(p.upper().replace("-", "_")[:8] for p in parts[:-1] + [parts[-1].upper().split(".")[0][:8] + ("." + parts[-1].split(".")[1].upper()[:3] if "." in parts[-1] else "")]) + ";1"
        iso.add_fp(io.BytesIO(data), len(data), iso_name, joliet_path="/" + rel, udf_path="/" + rel)
    iso.write(str(path))
    iso.close()


def test_real_iso_structure_accepted(tmp_path):
    p = tmp_path / "test.iso"
    build_iso(p)
    assert check_iso_structure(p, min_size=0) in ("UDF", "ISO9660")


def test_random_file_is_not_an_iso(tmp_path):
    p = tmp_path / "bad.iso"
    p.write_bytes(b"\x00" * 200_000)
    with pytest.raises(InvalidIsoError):
        check_iso_structure(p, min_size=0)


def test_truncated_or_html_error_page_rejected(tmp_path):
    p = tmp_path / "bad.iso"
    p.write_bytes(b"<html>403 Forbidden</html>")
    with pytest.raises(InvalidIsoError, match="too small"):
        check_iso_structure(p)


def test_checksum_match_and_mismatch(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"hello" * 1000)
    good = hashlib.sha256(p.read_bytes()).hexdigest()
    assert verify_checksum(p, "sha256", good.upper()) == good
    with pytest.raises(ChecksumMismatchError):
        verify_checksum(p, "sha256", "0" * 64)
    assert hash_file(p, "sha1") == hashlib.sha1(p.read_bytes()).hexdigest()


def entries(**overrides):
    files = {k: len(v) for k, v in ISO_FILES.items()}
    files.update(overrides)
    return [FileEntry(k, v) for k, v in files.items() if v is not None]


def test_layout_of_winpe_tree():
    layout = analyse_layout(entries())
    assert layout.supports_uefi and layout.supports_bios
    assert layout.wim_images == ["sources/boot.wim"]
    assert len(layout.bcd_stores) == 2


def test_layout_missing_parts():
    with pytest.raises(InvalidIsoError, match="BOOTX64"):
        analyse_layout(entries(**{"EFI/BOOT/BOOTX64.EFI": None}))
    with pytest.raises(InvalidIsoError, match=".wim"):
        analyse_layout(entries(**{"sources/boot.wim": None}))
    assert not analyse_layout(entries(bootmgr=None)).supports_bios


def test_file_over_fat32_limit_rejected():
    with pytest.raises(InvalidIsoError, match="larger than 4 GB"):
        analyse_layout(entries(**{"sources/boot.wim": config.FAT32_MAX_FILE_BYTES + 1}))


def test_mbr_parsing():
    sig, code, parts = parse_mbr(good_mbr())
    assert sig and code and len(parts) == 1 and parts[0].active and parts[0].type_id == 0x0C
    assert mbr_problems(good_mbr()) == []
    assert "partition is not marked active" in mbr_problems(good_mbr(active=False))
    assert any("not FAT32" in p for p in mbr_problems(good_mbr(ptype=0x07)))
    assert any("boot code" in p for p in mbr_problems(good_mbr(boot_code=False)))
    assert "MBR signature missing" in mbr_problems(b"\0" * 512)


def test_pbr_parsing():
    assert pbr_info(good_pbr()) == (True, "BOOTMGR")
    assert pbr_info(good_pbr(b"NTLDR")) == (True, "NTLDR")
    assert pbr_info(b"\0" * 1024) == (False, None)


def test_copy_and_readback_verification(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    for rel, data in ISO_FILES.items():
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_bytes(data)
    tree = list_tree(src)
    hashes = copy_tree(src, dst, tree)
    verify_tree(dst, tree, hashes)  # uses the uncached reader (plain reads off-Windows)
    (dst / "bootmgr").write_bytes(b"corrupted")
    with pytest.raises(UsbWriteError):
        verify_tree(dst, tree, hashes)
