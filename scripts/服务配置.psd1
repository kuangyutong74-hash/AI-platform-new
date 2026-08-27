@{
  Services = @(
    @{ Name='统一账号与证据中心'; Port=8020; WorkingDirectory='modules\platform-core'; Command='python'; Arguments=@('main.py'); Url='http://localhost:8020/api/health' },
    @{ Name='报告生成服务'; Port=8030; WorkingDirectory='modules\report-agent'; Command='python'; Arguments=@('main.py'); Url='http://localhost:8030/health' },
    @{ Name='聊天观察'; Port=3000; WorkingDirectory='modules\chat'; Command='node'; Arguments=@('app.js'); Url='http://localhost:3000/chat.html?from=ai-bole' },
    @{ Name='故事共创后端'; Port=8010; WorkingDirectory='modules\story\backend'; Command='python'; Arguments=@('-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8010'); Url='http://localhost:8010/api/health' },
    @{ Name='故事共创前端'; Port=5174; WorkingDirectory='modules\story\frontend'; Command='npm'; Arguments=@('run','dev','--','--strictPort','--port','5174'); Url='http://localhost:5174/story-create?from=ai-bole' },
    @{ Name='深海基地后端'; Port=8005; WorkingDirectory='modules\deep-sea'; Command='python'; Arguments=@('server/server.py'); Url='http://localhost:8005/api/health' },
    @{ Name='深海基地前端'; Port=3001; WorkingDirectory='modules\deep-sea'; Command='npm'; Arguments=@('run','dev','--','--strictPort','--port','3001'); Url='http://localhost:3001/?from=ai-bole' },
    @{ Name='职业模拟器'; Port=8000; WorkingDirectory='modules\career\backend'; Command='python'; Arguments=@('main.py'); Url='http://127.0.0.1:8000/?from=ai-bole' },
    @{ Name='天赋报告'; Port=5175; WorkingDirectory='modules\talent-report'; Command='npm'; Arguments=@('run','dev','--','--strictPort'); Url='http://localhost:5175/?from=ai-bole' },
    @{ Name='整合平台'; Port=4173; WorkingDirectory='.'; Command='npm'; Arguments=@('run','start'); Url='http://localhost:4173' }
  )
}
