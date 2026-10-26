# Corex Boot

Corex Boot is a Windows 10/11 (64-bit) desktop app that downloads the official
**Hiren's BootCD PE** ISO and turns a USB flash drive into a bootable Hiren's
USB. It is built to need almost no instructions:

1. Plug in a USB flash drive (8 GB or larger) and start **CorexBoot.exe**. Windows asks
   for Administrator permission; choose **Yes**.
2. Pick the USB drive in the list. Corex Boot never selects a drive for you.
3. Click **Download & Create USB**, check the details in the confirmation box, tick
   *"I understand…"* and click **Erase and create USB**.
4. Wait for **✔ Bootable USB Ready**.

Corex Boot does one thing only: it creates a bootable Hiren's BootCD PE USB drive.
It never touches internal disks. It does not install Windows, recover passwords or
bypass encryption.

---

## 1. Official source and checksum policy

| | |
|---|---|
| Release page | `https://www.hirensbootcd.org/download/`, the only page Corex Boot reads release data from |
| ISO URL | Read from that page **at runtime** (an `<a href>` ending in `.iso`). No version or URL is hardcoded. |
| Allowed hosts | `hirensbootcd.org` and its subdomains, **HTTPS only**. Links to other hosts are ignored. A redirect that leaves the domain stops the download. |
| Checksum | Read from the same page at runtime (SHA-256 preferred, then SHA-1, then MD5). If the page lists conflicting values for an algorithm, that algorithm is not used. |
| No usable checksum | The user sees a warning: *"…CANNOT be verified as authentic… Continue with an unverified ISO?"* (default **No**). If they continue, the result screen says **"The ISO was NOT checksum-verified"** and never claims it was. |
| Checksum mismatch | The ISO is deleted, nothing is written to the USB drive, and the user is asked to retry. |

The ISO must also pass a structure check (ISO 9660/UDF volume descriptors) and a
WinPE layout check (`EFI/BOOT/BOOTX64.EFI`, a BCD store and a `.wim` image, no
file larger than FAT32's 4 GB limit). Both checks run **before the USB drive is erased**.

> Note from development: the build environment's network policy blocked
> `hirensbootcd.org`, so the live page could not be inspected while writing this
> code. The parser is written for the page's known layout (an `.iso` link plus
> labelled MD5/SHA-1/SHA-256 values) and fails safe if that layout changes. It
> then reports *"Could not find the ISO download link"* and offers to continue
> unverified only when no checksum can be read. Run the first real download on
> Windows while watching the log to confirm the parser matches today's page.

## 2. USB creation engine: evaluation and choice

| Option | License | Unattended CLI | UEFI | Secure Boot | Verdict |
|---|---|---|---|---|---|
| **Rufus** | GPL-3.0 | **No.** The Rufus FAQ says command-line support is "very low priority"; the documented flags only pre-fill the GUI. | Yes | Yes | Best manual tool, but cannot be automated through a documented interface. Recommended as the **manual fallback** (§8). |
| **Ventoy** | GPL-3.0 | Yes (`Ventoy2Disk.exe VTOYCLI`) | Yes | Needs one-time MOK key enrolment on each PC | Works with HBCD PE, but adds a third-party bootloader and a Secure Boot enrolment step that non-technical staff cannot do. Not used. |
| **Hiren's ISO2USB** | Freeware, closed source | Not documented | Yes | Yes | No documented automation interface. Not used. |
| Raw write (`dd`-style) of the ISO | n/a | Yes | **Not reliable** | n/a | HBCD PE is not a hybrid ISO, so a raw write is not guaranteed to boot. Rejected. |
| **Microsoft WinPE USB method** (chosen) | Built into Windows | Yes (PowerShell Storage cmdlets) | Yes | **Yes** (keeps Microsoft-signed loaders) | Microsoft's documented way to make WinPE USB media; Hiren's BootCD PE is a WinPE 11 build. |

**Chosen method.** These are the steps Microsoft documents for *"Create a bootable
WinPE USB drive"*, run through Windows' built-in, documented PowerShell Storage
cmdlets:

1. `Clear-Disk -RemoveData -RemoveOEM` on the **one** confirmed disk, then
   `Initialize-Disk -PartitionStyle MBR`. The script re-checks the disk identity
   first (see §3).
2. `New-Partition -IsActive -MbrType FAT32` creates one partition of at most 31 GiB,
   because Windows will not format FAT32 above 32 GB. Then `Format-Volume -FileSystem FAT32`.
   - FAT32 is required by UEFI firmware.
   - The active MBR partition and Windows' NT6 FAT32 boot sector (which loads
     `BOOTMGR`) give legacy-BIOS boot.
3. `Mount-DiskImage -Access ReadOnly` mounts the ISO, and every file is copied to the
   USB drive while its SHA-256 is computed.
4. Every file is read back **uncached** (`FILE_FLAG_NO_BUFFERING`) from the USB drive
   and compared with the source hash.

No third-party binaries are bundled. Nothing from the ISO is ever executed.

## 3. Disk safety

Several independent layers have to agree before anything is erased:

1. **Discovery filter** (`usb_detect.rejection_reasons`). A disk is offered only if it meets all of these:
   - Bus type is `USB`.
   - It is not `IsBoot` or `IsSystem`.
   - It does not hold the Windows drive or the page file.
   - It has media, is 1 GB–2 TB in size, and is not write-protected.
   - Its `UniqueId` is non-empty and not shared with another disk.

   Internal NVMe/SATA/RAID disks and virtual disks are never listed. The hint line
   says how many disks were hidden, and the tooltip says why.
2. **No automatic selection.** The list always opens on *"Select a USB drive…"*, even
   when only one drive is present. A refresh keeps the user's choice only if the
   device is identical: same number, `UniqueId`, serial, size and name.
3. **Explicit confirmation.** A dialog shows the device name, capacity, drive letter,
   disk identifier (`Disk N (\\.\PhysicalDriveN)`) and serial number. The erase button
   stays disabled until *"I understand…"* is ticked. **Cancel** is the default button.
4. **Revalidation right before writing** (`disk_safety.revalidate`). Windows is queried
   again after the download and immediately before the erase.
   - If the drive was unplugged, replaced, resized, renumbered or has become
     ambiguous, the run stops with *"Nothing was written"*.
   - It never switches to a different disk.
5. **Revalidation inside the erase script** (`prepare_disk.ps1`). In the same PowerShell
   process, immediately before `Clear-Disk`, the script re-checks the disk number,
   `UniqueId`, exact size, bus type `USB`, boot/system flags, identifier uniqueness and
   the system drive letter. Any mismatch exits with `SAFETY:` before anything changes.
6. **Disconnects during writing** are detected (I/O error followed by a rescan). The
   user is told the drive was disconnected and that it is incomplete.
7. While a USB drive is being written, **Cancel** is disabled and closing the window
   asks for confirmation.

## 4. How bootability is verified, and what is *not* claimed

**✔ Bootable USB Ready** is shown only after every one of these checks passes:

| Check | How |
|---|---|
| ISO authentic | Published SHA-256 (or SHA-1/MD5) matches. If no checksum was available, this is reported as a warning instead. |
| ISO is bootable WinPE | UEFI loader, BCD store and `.wim` present; no file over 4 GB |
| Every byte copied correctly | All files read back uncached and SHA-256-compared with the ISO |
| Partition table | MBR signature `55AA`, exactly one partition, marked **active**, type FAT32 (`0x0B`/`0x0C`) |
| File system | Volume boot sector reports `FAT32` |
| UEFI boot path | `EFI/BOOT/BOOTX64.EFI` present on the USB drive |
| Legacy BIOS boot path | MBR boot code present, and the FAT32 boot sector loads `BOOTMGR`. If this cannot be confirmed, it is shown as a **warning** ("expected to boot on UEFI computers") rather than a pass. |

These checks show that the USB drive has the same on-disk structure as Microsoft's
WinPE media with a byte-identical copy of the ISO. **They are not a boot test.**
Firmware differs between computers, so the completion screen always tells the user
to do the final check: boot a PC from the drive (boot menu key, usually F12, F11 or Esc).

## 5. Building

**On Windows (produces `dist\CorexBoot.exe`):**

```powershell
cd corex-boot
powershell -ExecutionPolicy Bypass -File build.ps1      # or double-click build.bat
```

`build.ps1` does the following:

1. Creates `.venv` with Python 3.12 or later.
2. Installs `requirements-dev.txt`.
3. Runs the test suite and stops if anything fails.
4. Runs `PyInstaller corex_boot.spec`, which builds a one-file, windowed EXE with a UAC
   `requireAdministrator` manifest, an icon and version info.

**In CI:** `.github/workflows/corex-boot.yml` runs on `windows-latest`. It runs the
unit/GUI tests and the real-Windows integration tests, builds the EXE, smoke-tests it
with `CorexBoot.exe --self-test`, and uploads `CorexBoot.exe` as the
`CorexBoot-windows-x64` build artifact.

The final executable location is `corex-boot/dist/CorexBoot.exe`.

## 6. Tests

```powershell
python -m pytest -q                         # everything that runs anywhere (Linux/macOS/Windows)
$env:COREX_WINDOWS_INTEGRATION=1; python -m pytest tests/test_windows_integration.py
```

| QA scenario | Where it is tested |
|---|---|
| No USB connected | `test_usb_detect::test_no_usb_connected_offers_nothing`, `test_gui::test_no_usb_connected`, real scan in `test_windows_integration` |
| One USB connected | `test_usb_detect::test_one_usb_connected`, `test_gui::test_one_usb_is_listed_but_not_auto_selected` |
| Multiple USB drives | `test_usb_detect::test_multiple_usb_drives_sorted`, `test_gui::test_multiple_usb_not_auto_selected` |
| USB disconnected during operation | `test_workflow::test_usb_disconnected_during_download`, `…_during_write`, `test_disk_safety::test_disconnected_disk` |
| Download interrupted | `test_downloader::test_interrupted_download_resumes_with_range`, `…resume_across_program_restart`, `…server_ignoring_range…`, `test_workflow::test_download_interrupted` |
| Invalid ISO | `test_iso_and_boot::test_random_file_is_not_an_iso`, `…html_error_page_rejected`, `test_workflow::test_invalid_iso_file`, `…without_uefi_loader…`, checksum mismatch |
| Insufficient permissions | `test_workflow::test_insufficient_permissions` |
| Insufficient USB capacity | `test_disk_safety::test_capacity_*`, `test_workflow::test_insufficient_usb_capacity`, `test_downloader::test_insufficient_usb_capacity_aborts_download_early` |
| USB write failure | `test_workflow::test_usb_write_failure`, `…readback_mismatch_detected`, `…prepare_failure…`, `test_gui::test_failure_is_shown` |
| Incorrect disk selection | `test_disk_safety` (swapped, renumbered, resized, internal, ambiguous), `test_workflow::test_incorrect_disk_selection_internal_disk`, `test_usb_detect::test_internal_disks_never_offered`, integration: erase script refuses the wrong ID, a non-USB bus **and the real Windows system disk** |
| Successful creation | `test_workflow::test_successful_creation`, `test_gui::test_full_run_shows_bootable_usb_ready`, integration: real partition, format, mount, copy, uncached read-back, MBR/PBR check on a VHD |

The integration tests marked "disposable CI VM only" (`COREX_DESTRUCTIVE_CI=1`) create
a VHD and deliberately point the erase script at the system disk to prove it refuses.
**Never set that variable on a real PC.**

## 7. Files, logs and cleanup

- Download cache: `%LOCALAPPDATA%\CorexBoot\cache\`. It holds the ISO, the `.part`
  file and resume metadata. Everything is deleted after a successful run. After a
  failure the files are kept so the next run resumes or reuses the download.
- Logs: `%LOCALAPPDATA%\CorexBoot\logs\corex_boot.log` (rotating). Open it with the
  **Open log folder** button.

## 8. Limitations and fallback

- The boot partition is capped at 31 GiB (Windows' FAT32 limit). The rest of a larger
  drive is left unallocated.
- The USB drive uses MBR, which UEFI and legacy BIOS firmware both boot. This is
  Microsoft's WinPE layout.
- If the official page layout changes and Corex Boot cannot find the ISO link, or the
  site moves the download outside `hirensbootcd.org`, Corex Boot stops instead of
  guessing. Manual fallback:
  1. Download the ISO from the official page.
  2. Compare `Get-FileHash HBCD_PE_x64.iso -Algorithm SHA256` with the published value.
  3. Write it with **Rufus**: Partition scheme MBR, Target "BIOS or UEFI", File system FAT32.

## Project layout

```
corex-boot/
  src/corex_boot/
    app.py              entry point, UAC elevation, --self-test
    config.py           official domain, size limits (no versions or checksums)
    source.py           official page discovery and parsing
    net.py / downloader.py   HTTPS-only, domain-locked, resumable download
    iso_verify.py       checksum and ISO structure
    usb_detect.py       disk enumeration and safety classification
    disk_safety.py      pre-write revalidation and capacity
    backend.py          Windows side effects (injectable for tests)
    usb_copy.py / winio.py   copy, uncached read-back
    boot_verify.py      WinPE layout, MBR and PBR checks
    workflow.py         end-to-end orchestration
    gui/                PySide6 window, confirmation dialog, worker threads
    scripts/*.ps1       Get-Disk / Clear-Disk / Format-Volume / Mount-DiskImage wrappers
  tests/                pytest suite (unit, GUI, downloader, Windows integration)
  corex_boot.spec, build.ps1, build.bat, requirements*.txt
```
