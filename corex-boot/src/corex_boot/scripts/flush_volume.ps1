param([Parameter(Mandatory = $true)][string]$DriveLetter)
$ErrorActionPreference = 'Stop'
try {
    Write-VolumeCache -DriveLetter $DriveLetter
    '{"Flushed":true}'
} catch {
    [Console]::Error.WriteLine("COREX_ERROR: $($_.Exception.Message)")
    exit 1
}
