# Erases ONE disk and creates a single active FAT32 partition (MBR), the layout Microsoft
# documents for bootable WinPE USB media (UEFI + legacy BIOS).
# The disk identity is re-checked inside this script, immediately before Clear-Disk,
# so the disk erased is exactly the one the user confirmed.
param(
    [Parameter(Mandatory = $true)][int]$DiskNumber,
    [Parameter(Mandatory = $true)][string]$ExpectedUniqueId,
    [Parameter(Mandatory = $true)][int64]$ExpectedSize,
    [Parameter(Mandatory = $true)][string]$ExpectedBusType,
    [Parameter(Mandatory = $true)][int64]$MaxPartitionBytes,
    [Parameter(Mandatory = $true)][string]$Label
)
$ErrorActionPreference = 'Stop'
function Fail($msg) { [Console]::Error.WriteLine("COREX_ERROR: $msg"); exit 2 }

try {
    $d = Get-Disk -Number $DiskNumber -ErrorAction SilentlyContinue
    if (-not $d) { Fail "SAFETY: disk $DiskNumber is no longer present. Nothing was written." }
    if ([string]$d.UniqueId -ne $ExpectedUniqueId) { Fail "SAFETY: disk $DiskNumber identity changed. Nothing was written." }
    if ([int64]$d.Size -ne $ExpectedSize) { Fail "SAFETY: disk $DiskNumber size changed. Nothing was written." }
    if ([string]$d.BusType -ne $ExpectedBusType) { Fail "SAFETY: disk $DiskNumber is not a $ExpectedBusType device. Nothing was written." }
    if ($d.IsBoot -or $d.IsSystem) { Fail "SAFETY: disk $DiskNumber is a Windows system/boot disk. Nothing was written." }
    $sameId = @(Get-Disk | Where-Object { [string]$_.UniqueId -eq $ExpectedUniqueId })
    if ($sameId.Count -ne 1) { Fail "SAFETY: disk identifier is ambiguous. Nothing was written." }
    $sysLetter = ([string]$env:SystemDrive).Substring(0, 1)
    $letters = @(Get-Partition -DiskNumber $DiskNumber -ErrorAction SilentlyContinue | ForEach-Object { [string]$_.DriveLetter })
    if ($letters -contains $sysLetter) { Fail "SAFETY: disk holds the Windows drive. Nothing was written." }

    if ($d.IsOffline) { Set-Disk -Number $DiskNumber -IsOffline $false }
    if ($d.IsReadOnly) { Set-Disk -Number $DiskNumber -IsReadOnly $false }

    if ([string]$d.PartitionStyle -ne 'RAW') {
        Clear-Disk -Number $DiskNumber -RemoveData -RemoveOEM -Confirm:$false
    }
    Initialize-Disk -Number $DiskNumber -PartitionStyle MBR
    $free = [int64](Get-Disk -Number $DiskNumber).LargestFreeExtent
    $size = [Math]::Min($free, $MaxPartitionBytes)
    $size = $size - ($size % 1MB)
    $p = New-Partition -DiskNumber $DiskNumber -Size $size -IsActive -MbrType FAT32
    $null = Format-Volume -Partition $p -FileSystem FAT32 -NewFileSystemLabel $Label -Confirm:$false -Force
    $p = Get-Partition -DiskNumber $DiskNumber -PartitionNumber $p.PartitionNumber
    if (-not $p.DriveLetter -or [int][char]$p.DriveLetter -eq 0) {
        $p | Add-PartitionAccessPath -AssignDriveLetter
        $p = Get-Partition -DiskNumber $DiskNumber -PartitionNumber $p.PartitionNumber
    }
    if (-not $p.DriveLetter -or [int][char]$p.DriveLetter -eq 0) { Fail "Windows did not assign a drive letter to the USB drive." }

    [pscustomobject]@{
        DriveLetter     = [string]$p.DriveLetter
        PartitionNumber = [int]$p.PartitionNumber
        PartitionSize   = [int64]$p.Size
    } | ConvertTo-Json -Compress
} catch {
    [Console]::Error.WriteLine("COREX_ERROR: $($_.Exception.Message)")
    exit 1
}
