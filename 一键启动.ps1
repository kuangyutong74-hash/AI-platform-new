param(
  [switch]$NoOpen,
  [switch]$Restart,
  [ValidateRange(10, 180)][int]$TimeoutSeconds = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\scripts\服务工具.ps1"

$runtimeDirectory = Get-RuntimeDirectory
$logDirectory = Join-Path $runtimeDirectory 'logs'
$registryPath = Join-Path $runtimeDirectory 'services.json'
if (-not (Test-Path -LiteralPath $logDirectory)) {
  New-Item -ItemType Directory -Path $logDirectory | Out-Null
}

if ($Restart -and (Test-Path -LiteralPath $registryPath)) {
  Write-Host '正在停止上次由本项目启动的服务…' -ForegroundColor Cyan
  & "$PSScriptRoot\停止全部服务.ps1"
  Start-Sleep -Milliseconds 800
}

if ($Restart) {
  Write-Host '正在回收配置端口上的残留服务…' -ForegroundColor Cyan
  foreach ($service in @(Get-ServiceDefinitions)) {
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $service.Port -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
      if ($listener.OwningProcess -and $listener.OwningProcess -ne $PID) {
        Stop-ServiceProcessTree -ServiceProcessId $listener.OwningProcess
        Write-Host "[已回收] $($service.Name) 端口 $($service.Port)" -ForegroundColor DarkGray
      }
    }
  }
  Start-Sleep -Milliseconds 800
}

$registered = @()
if (Test-Path -LiteralPath $registryPath) {
  try {
    $saved = Get-Content -Raw -Encoding UTF8 -LiteralPath $registryPath | ConvertFrom-Json -ErrorAction Stop
    $registered = @(Convert-ServiceRegistryEntries -Entries @($saved) | Where-Object {
      Get-Process -Id $_.Pid -ErrorAction SilentlyContinue
    })
  } catch {
    $backup = "$registryPath.corrupt.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Move-Item -LiteralPath $registryPath -Destination $backup -Force
    Write-Warning "旧服务记录已损坏，已保留备份并重新建立：$backup"
  }
}

$started = [System.Collections.Generic.List[object]]::new()
$conflicts = [System.Collections.Generic.List[object]]::new()
$services = @(Get-ServiceDefinitions)
$platformService = $services | Where-Object Name -eq '整合平台' | Select-Object -First 1
$platformBuildLog = Join-Path $logDirectory '整合平台.build.log'

Write-Host "`nAI伯乐一键启动" -ForegroundColor Cyan
Write-Host '正在检查端口并启动所需服务，请稍候…' -ForegroundColor DarkGray

# Build the shell before starting the module development servers. On a cold
# start, several Vite instances optimize dependencies at once; building the
# shell at the same time can exhaust resources and leave an incomplete build.
if ($platformService -and -not (Test-ServiceEndpoint $platformService.Url)) {
  $platformCommand = Resolve-ServiceCommand $platformService.Command $platformService.WorkingDirectory
  Write-Host '[构建中] 整合平台前端' -ForegroundColor Yellow
  Push-Location $platformService.WorkingDirectory
  try {
    # PowerShell 5.1 turns npm.cmd stderr lines into NativeCommandError records;
    # with $ErrorActionPreference='Stop' the first one aborts the script mid-build.
    # Downgrade to Continue for the build; real failures are caught via $LASTEXITCODE.
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
      & $platformCommand run build *> $platformBuildLog
    } finally {
      $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($LASTEXITCODE -ne 0) {
      throw "前端构建失败（退出码 $LASTEXITCODE），请查看：$platformBuildLog"
    }
  } finally {
    Pop-Location
  }
}

foreach ($service in $services) {
  if (Test-ServiceEndpoint $service.Url) {
    Write-Host ("[已就绪] {0,-18} {1}" -f $service.Name, $service.Url) -ForegroundColor DarkGray
    continue
  }

  if (Test-ServicePort $service.Port) {
    $conflicts.Add($service)
    Write-Warning "端口 $($service.Port) 已被其他进程占用，但 $($service.Name) 无法访问。"
    continue
  }

  if (-not (Test-Path -LiteralPath $service.WorkingDirectory)) {
    $conflicts.Add($service)
    Write-Warning "目录不存在，无法启动 $($service.Name)：$($service.WorkingDirectory)"
    continue
  }

  $safeName = $service.Name -replace '[\\/:*?"<>|]', '_'
  $stdout = Join-Path $logDirectory "$safeName.out.log"
  $stderr = Join-Path $logDirectory "$safeName.err.log"
  try {
    $command = Resolve-ServiceCommand $service.Command $service.WorkingDirectory
    $process = Start-Process -FilePath $command -ArgumentList $service.Arguments `
      -WorkingDirectory $service.WorkingDirectory -WindowStyle Hidden -PassThru `
      -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $record = [pscustomobject]@{
      Name = $service.Name
      Port = $service.Port
      Pid = $process.Id
      Url = $service.Url
      ErrorLog = $stderr
    }
    $started.Add($record)
    Write-Host ("[启动中] {0,-18} PID {1}" -f $service.Name, $process.Id) -ForegroundColor Yellow
  } catch {
    $conflicts.Add($service)
    Write-Warning "启动 $($service.Name) 失败：$($_.Exception.Message)"
  }
}

$allRecords = @(@($registered) + @($started))
$registryJson = if ($allRecords.Count -gt 0) {
  $allRecords | ConvertTo-Json -Depth 4
} else {
  '[]'
}
$registryJson | Set-Content -LiteralPath $registryPath -Encoding UTF8

$pending = @($started)
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ($pending.Count -gt 0 -and (Get-Date) -lt $deadline) {
  $remaining = @()
  foreach ($record in $pending) {
    if (Test-ServiceEndpoint $record.Url) {
      Write-Host ("[已就绪] {0,-18} {1}" -f $record.Name, $record.Url) -ForegroundColor Green
    } elseif (-not (Get-Process -Id $record.Pid -ErrorAction SilentlyContinue)) {
      $service = $services | Where-Object Name -eq $record.Name | Select-Object -First 1
      if ($service) { $conflicts.Add($service) }
      Write-Warning "$($record.Name) 已提前退出，请查看：$($record.ErrorLog)"
    } else {
      $remaining += $record
    }
  }
  $pending = @($remaining)
  if ($pending.Count -gt 0) { Start-Sleep -Milliseconds 700 }
}

foreach ($record in $pending) {
  $service = $services | Where-Object Name -eq $record.Name | Select-Object -First 1
  if ($service) { $conflicts.Add($service) }
  Write-Warning "$($record.Name) 在 $TimeoutSeconds 秒内没有就绪，请查看：$($record.ErrorLog)"
}

$platformUrl = 'http://localhost:4173'
$platformReady = Test-ServiceEndpoint $platformUrl
Write-Host "`n启动结果" -ForegroundColor Cyan
foreach ($service in $services) {
  $ready = Test-ServiceEndpoint $service.Url
  $label = if ($ready) { '可访问' } else { '未就绪' }
  $color = if ($ready) { 'Green' } else { 'Red' }
  Write-Host ("{0,-18} {1,-6} {2}" -f $service.Name, $label, $service.Url) -ForegroundColor $color
}

if ($platformReady -and -not $NoOpen) {
  Start-Process $platformUrl
}

if (-not $platformReady) {
  throw "整合平台前端未能启动。请查看 $platformBuildLog 和 $(Join-Path $logDirectory '整合平台.err.log')。"
}
if ($conflicts.Count -gt 0 -or $pending.Count -gt 0) {
  Write-Warning "首页已启动，但部分模块未就绪。日志目录：$logDirectory"
} else {
  Write-Host "`n全部服务已就绪：$platformUrl" -ForegroundColor Green
}
