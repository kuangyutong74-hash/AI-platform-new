@{
  Services = @(
    @{ Name='聊天观察'; Port=3000; WorkingDirectory='modules\chat'; Command='node'; Arguments=@('app.js'); Url='http://localhost:3000/chat.html?from=ai-bole' },
    @{ Name='故事共创后端'; Port=8010; WorkingDirectory='modules\story\backend'; Command='python'; Arguments=@('-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8010'); Url='http://localhost:8010/api/health' },
    @{ Name='故事共创前端'; Port=5174; WorkingDirectory='modules\story\frontend'; Command='npm'; Arguments=@('run','dev'); Url='http://localhost:5174/story-create?from=ai-bole' },
    @{ Name='深海基地后端'; Port=8005; WorkingDirectory='modules\deep-sea'; Command='python'; Arguments=@('server/server.py'); Url='http://localhost:8005/api/health' },
    @{ Name='深海基地前端'; Port=3001; WorkingDirectory='modules\deep-sea'; Command='npm'; Arguments=@('run','dev'); Url='http://localhost:3001/?from=ai-bole' },
    @{ Name='职业模拟器'; Port=8000; WorkingDirectory='modules\career\backend'; Command='python'; Arguments=@('main.py'); Url='http://127.0.0.1:8000/?from=ai-bole' },
    @{ Name='整合平台'; Port=4173; WorkingDirectory='.'; Command='npm'; Arguments=@('run','dev'); Url='http://localhost:4173' }
  )
}
