Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Checked([scriptblock]$Action, [string]$FailureMessage) {
  & $Action
  if ($LASTEXITCODE -ne 0) { throw "$FailureMessage（退出码 $LASTEXITCODE）" }
}

$platform = $PSScriptRoot
$nodeProjects = @(
  $platform
  (Join-Path $platform 'modules\chat')
  (Join-Path $platform 'modules\story\frontend')
  (Join-Path $platform 'modules\deep-sea')
  (Join-Path $platform 'modules\talent-report')
)
$pythonProjects = @(
  @{ WorkingDirectory=(Join-Path $platform 'modules\story\backend'); Requirements='requirements.txt' }
  @{ WorkingDirectory=(Join-Path $platform 'modules\deep-sea'); Requirements='server\requirements.txt' }
  @{ WorkingDirectory=(Join-Path $platform 'modules\career\backend'); Requirements='requirements.txt' }
  @{ WorkingDirectory=(Join-Path $platform 'modules\platform-core'); Requirements='requirements.txt' }
  @{ WorkingDirectory=(Join-Path $platform 'modules\report-agent'); Requirements='requirements.txt' }
)

$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) { $npm = Get-Command npm -ErrorAction Stop }
$python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction Stop }

foreach ($project in $nodeProjects) {
  Write-Host "[Node.js] $project" -ForegroundColor Cyan
  Push-Location $project
  try {
    Invoke-Checked { & $npm.Source install --no-audit --no-fund } "Node.js 依赖安装失败：$project"
  } finally {
    Pop-Location
  }
}

foreach ($project in $pythonProjects) {
  $workingDirectory = $project.WorkingDirectory
  $requirements = Join-Path $workingDirectory $project.Requirements
  $venvDirectory = Join-Path $workingDirectory '.venv'
  $venvPython = Join-Path $venvDirectory 'Scripts\python.exe'

  Write-Host "[Python] $workingDirectory" -ForegroundColor Cyan
  if (-not (Test-Path -LiteralPath $venvPython)) {
    Invoke-Checked { & $python.Source -m venv $venvDirectory } "Python 虚拟环境创建失败：$workingDirectory"
  }
  Invoke-Checked { & $venvPython -m pip install --disable-pip-version-check -r $requirements } "Python 依赖安装失败：$requirements"
}

Write-Host '全部依赖安装完成。' -ForegroundColor Green
