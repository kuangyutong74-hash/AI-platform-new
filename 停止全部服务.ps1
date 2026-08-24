. "$PSScriptRoot\scripts\服务工具.ps1"

$runtime = Get-RuntimeDirectory
$registry = Join-Path $runtime 'services.json'
if (-not (Test-Path -LiteralPath $registry)) {
  Write-Host '没有找到本平台启动的服务记录，无需停止。' -ForegroundColor DarkGray
  exit 0
}

$saved = Get-Content -Raw -LiteralPath $registry | ConvertFrom-Json
$records = @(Convert-ServiceRegistryEntries -Entries @($saved))
foreach ($record in $records) {
  $process = Get-Process -Id $record.Pid -ErrorAction SilentlyContinue
  if ($process) {
    Stop-ServiceProcessTree -ServiceProcessId $record.Pid
    Write-Host "[已停止] $($record.Name) (PID $($record.Pid))" -ForegroundColor Green
  }
}
Remove-Item -LiteralPath $registry
