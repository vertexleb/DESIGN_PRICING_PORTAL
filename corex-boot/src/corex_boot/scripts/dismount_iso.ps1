param([Parameter(Mandatory = $true)][string]$ImagePath)
$ErrorActionPreference = 'Stop'
try {
    $img = Get-DiskImage -ImagePath $ImagePath -ErrorAction SilentlyContinue
    if ($img -and $img.Attached) { $null = Dismount-DiskImage -ImagePath $ImagePath }
    '{"Dismounted":true}'
} catch {
    [Console]::Error.WriteLine("COREX_ERROR: $($_.Exception.Message)")
    exit 1
}
