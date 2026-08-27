Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-PlatformRoot { Split-Path -Parent $PSScriptRoot }

function Get-ServiceDefinitions {
  $config = Import-PowerShellDataFile -LiteralPath (Join-Path $PSScriptRoot '服务配置.psd1')
  $root = Get-PlatformRoot
  foreach ($service in $config.Services) {
    [pscustomobject]@{
      Name = $service.Name
      Port = [int]$service.Port
      WorkingDirectory = Join-Path $root $service.WorkingDirectory
      Command = $service.Command
      Arguments = @($service.Arguments)
      Url = $service.Url
    }
  }
}

function Test-ServicePort([int]$Port) {
  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $task = $client.ConnectAsync('127.0.0.1', $Port)
    return $task.Wait(700) -and $client.Connected
  } catch {
    return $false
  } finally {
    $client.Dispose()
  }
}

function Test-ServiceEndpoint([string]$Url) {
  try {
    $response = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
  } catch {
    $responseProperty = $_.Exception.PSObject.Properties['Response']
    if ($responseProperty -and $responseProperty.Value) {
      $statusProperty = $responseProperty.Value.PSObject.Properties['StatusCode']
      if ($statusProperty -and [int]$statusProperty.Value -lt 500) { return $true }
    }
    return $false
  }
}

function Stop-ServiceProcessTree([int]$ServiceProcessId) {
  $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $ServiceProcessId" -ErrorAction SilentlyContinue)
  foreach ($child in $children) {
    Stop-ServiceProcessTree -ServiceProcessId $child.ProcessId
  }
  Stop-Process -Id $ServiceProcessId -Force -ErrorAction SilentlyContinue
}

function Resolve-ServiceCommand([string]$Command, [string]$WorkingDirectory) {
  if ($Command -eq 'npm') {
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npm) { $npm = Get-Command npm -ErrorAction Stop }
    return $npm.Source
  }
  if ($Command -eq 'python') {
    $localPython = Join-Path $WorkingDirectory '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $localPython) { return $localPython }
    $localPython = Join-Path $WorkingDirectory '.venv\bin\python.exe'
    if (Test-Path -LiteralPath $localPython) { return $localPython }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $python) { $python = Get-Command python -ErrorAction Stop }
    return $python.Source
  }
  return (Get-Command $Command -ErrorAction Stop).Source
}

function Get-RuntimeDirectory {
  $directory = Join-Path (Split-Path -Parent $PSScriptRoot) '.runtime'
  if (-not (Test-Path -LiteralPath $directory)) { New-Item -ItemType Directory -Path $directory | Out-Null }
  return $directory
}

function Convert-ServiceRegistryEntries([object[]]$Entries) {
  foreach ($entry in @($Entries)) {
    if ($null -eq $entry) { continue }
    if ($entry.PSObject.Properties['Pid'] -and $entry.PSObject.Properties['Name']) {
      $entry
      continue
    }
    if ($entry.PSObject.Properties['value']) {
      Convert-ServiceRegistryEntries -Entries @($entry.value)
    }
  }
}
