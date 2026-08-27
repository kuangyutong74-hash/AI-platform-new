. "$PSScriptRoot\scripts\服务工具.ps1"

$runtime = Get-RuntimeDirectory
$registry = Join-Path $runtime 'services.json'
if (-not (Test-Path -LiteralPath $registry)) {
  Write-Host '没有找到本平台启动的服务记录，无需停止。' -ForegroundColor DarkGray
  exit 0
}

$records = @()
try {
  $saved = Get-Content -Raw -Encoding UTF8 -LiteralPath $registry | ConvertFrom-Json -ErrorAction Stop
  $records = @(Convert-ServiceRegistryEntries -Entries @($saved))
} catch {
  $backup = "$registry.corrupt.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
  Move-Item -LiteralPath $registry -Destination $backup -Force
  Write-Warning "服务记录已损坏，已保留备份：$backup。重启流程将继续按配置端口回收服务。"
  return
}
foreach ($record in $records) {
  $process = Get-Process -Id $record.Pid -ErrorAction SilentlyContinue
  if ($process) {
    Stop-ServiceProcessTree -ServiceProcessId $record.Pid
    Write-Host "[已停止] $($record.Name) (PID $($record.Pid))" -ForegroundColor Green
  }
}
Remove-Item -LiteralPath $registry -Force
