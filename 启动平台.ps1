$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "未找到 npm。请先安装 Node.js 22.13 或更高版本。"
}

Write-Host "正在启动 AI伯乐·探索星球..." -ForegroundColor Cyan
Write-Host "启动后请访问 http://localhost:4173" -ForegroundColor Green
npm run dev
