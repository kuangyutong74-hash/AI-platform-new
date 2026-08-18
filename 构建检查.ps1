$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "未找到 npm。请先安装 Node.js 22.13 或更高版本。"
}

Write-Host "正在执行正式构建和页面测试..." -ForegroundColor Cyan
npm test
