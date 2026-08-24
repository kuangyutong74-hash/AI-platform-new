$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\scripts\服务工具.ps1"

$fixture = '[{"value":[{"Name":"整合平台","Port":4173,"Pid":101}],"Count":1},{"Name":"统一账号与证据中心","Port":8020,"Pid":202}]' | ConvertFrom-Json
$records = @(Convert-ServiceRegistryEntries -Entries $fixture)

if ($records.Count -ne 2) { throw "应当展开为 2 条服务记录，实际为 $($records.Count)" }
if (($records | Where-Object Name -eq '整合平台').Pid -ne 101) { throw '未保留嵌套的整合平台进程号' }
if (($records | Where-Object Name -eq '统一账号与证据中心').Pid -ne 202) { throw '未保留正常服务记录' }

Write-Output 'startup registry normalization: PASS'
