$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$moduleRoot = Join-Path $projectRoot 'modules\platform-core'
$python = Join-Path $moduleRoot '.venv\Scripts\python.exe'
$reportAgentRoot = Join-Path $projectRoot 'modules\report-agent'

if (-not (Test-Path -LiteralPath $python)) {
  throw '统一账号服务的 Python 环境尚未安装，请先运行“安装全部依赖.ps1”。'
}

Push-Location -LiteralPath $moduleRoot
try {
  & $python -m unittest discover -s 'tests' -p 'test_*.py'
  $testExitCode = $LASTEXITCODE
}
finally {
  Pop-Location
}

if ($testExitCode -ne 0) { exit $testExitCode }

Push-Location -LiteralPath $reportAgentRoot
try {
  & $python -m unittest discover -s 'tests' -p 'test_*.py'
  $testExitCode = $LASTEXITCODE
}
finally {
  Pop-Location
}

if ($testExitCode -ne 0) { exit $testExitCode }
