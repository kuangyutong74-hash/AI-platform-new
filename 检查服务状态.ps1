. "$PSScriptRoot\scripts\服务工具.ps1"

Write-Host "`nAI伯乐服务状态" -ForegroundColor Cyan
foreach ($service in Get-ServiceDefinitions) {
  $running = Test-ServicePort $service.Port
  $label = if ($running) { '运行中' } else { '未启动' }
  $color = if ($running) { 'Green' } else { 'Yellow' }
  Write-Host ("{0,-16} {1,-6} {2}" -f $service.Name, $label, $service.Url) -ForegroundColor $color
}
