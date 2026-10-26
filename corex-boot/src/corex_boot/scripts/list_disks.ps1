# Lists every disk with the attributes Corex Boot needs to decide what is a safe target.
# Read-only: performs no changes.
$ErrorActionPreference = 'Stop'
try {
    $pageFiles = @()
    try {
        $pageFiles = @(Get-CimInstance -ClassName Win32_PageFileUsage -ErrorAction Stop |
            ForEach-Object { ([string]$_.Name).Substring(0, 1) })
    } catch { }

    $disks = @(Get-Disk | ForEach-Object {
        $d = $_
        $letters = @(Get-Partition -DiskNumber $d.Number -ErrorAction SilentlyContinue |
            Where-Object { $_.DriveLetter -and [int][char]$_.DriveLetter -ne 0 } |
            ForEach-Object { [string]$_.DriveLetter })
        [pscustomobject]@{
            Number         = [int]$d.Number
            FriendlyName   = [string]$d.FriendlyName
            SerialNumber   = [string]$d.SerialNumber
            UniqueId       = [string]$d.UniqueId
            Size           = [int64]$d.Size
            BusType        = [string]$d.BusType
            IsBoot         = [bool]$d.IsBoot
            IsSystem       = [bool]$d.IsSystem
            IsOffline      = [bool]$d.IsOffline
            IsReadOnly     = [bool]$d.IsReadOnly
            PartitionStyle = [string]$d.PartitionStyle
            Location       = [string]$d.Location
            DriveLetters   = $letters
        }
    })
    $result = [pscustomobject]@{
        SystemDrive    = ([string]$env:SystemDrive).Substring(0, 1)
        PageFileDrives = $pageFiles
        Disks          = $disks
    }
    $result | ConvertTo-Json -Depth 5 -Compress
} catch {
    [Console]::Error.WriteLine("COREX_ERROR: $($_.Exception.Message)")
    exit 1
}
