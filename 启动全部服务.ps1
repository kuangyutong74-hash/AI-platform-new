param([switch]$NoOpen)
. "$PSScriptRoot\scripts\服务工具.ps1"

$runtime = Get-RuntimeDirectory
$logDirectory = Join-Path $runtime 'logs'
if (-not (Test-Path -LiteralPath $logDirectory)) { New-Item -ItemType Directory -Path $logDirectory | Out-Null }
$registryPath = Join-Path $runtime 'services.json'
$started = @()
if (Test-Path -LiteralPath $registryPath) {
  $started += @(Get-Content -Raw -LiteralPath $registryPath | ConvertFrom-Json | Where-Object { Get-Process -Id $_.Pid -ErrorAction SilentlyContinue })
}

foreach ($service in Get-ServiceDefinitions) {
  if (Test-ServicePort $service.Port) {
    Write-Host "[已运行] $($service.Name) 端口 $($service.Port)" -ForegroundColor DarkGray
    continue
  }
  if (-not (Test-Path -LiteralPath $service.WorkingDirectory)) {
    Write-Warning "跳过 $($service.Name)：目录不存在 $($service.WorkingDirectory)"
    continue
  }
  try {
    $command = Resolve-ServiceCommand $service.Command $service.WorkingDirectory
    $safeName = $service.Name -replace '[\\/:*?"<>|]', '_'
    $process = Start-Process -FilePath $command -ArgumentList $service.Arguments `
      -WorkingDirectory $service.WorkingDirectory -WindowStyle Hidden -PassThru `
      -RedirectStandardOutput (Join-Path $logDirectory "$safeName.out.log") `
      -RedirectStandardError (Join-Path $logDirectory "$safeName.err.log")
    $started += [pscustomobject]@{ Name=$service.Name; Port=$service.Port; Pid=$process.Id }
    Write-Host "[已启动] $($service.Name) (PID $($process.Id))" -ForegroundColor Green
  } catch {
    Write-Warning "启动 $($service.Name) 失败：$($_.Exception.Message)"
  }
}

$started | ConvertTo-Json | Set-Content -LiteralPath $registryPath -Encoding UTF8
Start-Sleep -Seconds 2
& "$PSScriptRoot\检查服务状态.ps1"
if (-not $NoOpen) { Start-Process 'http://localhost:4173' }
