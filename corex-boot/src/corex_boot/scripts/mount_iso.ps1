# Mounts an ISO read-only using Windows' built-in image mounting and reports its drive letter.
param([Parameter(Mandatory = $true)][string]$ImagePath)
$ErrorActionPreference = 'Stop'
try {
    $img = Get-DiskImage -ImagePath $ImagePath
    if (-not $img.Attached) { $img = Mount-DiskImage -ImagePath $ImagePath -StorageType ISO -Access ReadOnly -PassThru }
    $vol = $null
    for ($i = 0; $i -lt 20 -and -not $vol; $i++) {
        $vol = $img | Get-Volume -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter }
        if (-not $vol) { Start-Sleep -Milliseconds 500 }
    }
    if (-not $vol) { throw "The ISO was mounted but Windows did not assign it a drive letter." }
    [pscustomobject]@{
        DriveLetter = [string]$vol.DriveLetter
        Label       = [string]$vol.FileSystemLabel
    } | ConvertTo-Json -Compress
} catch {
    [Console]::Error.WriteLine("COREX_ERROR: $($_.Exception.Message)")
    exit 1
}
