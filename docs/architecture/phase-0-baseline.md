# 架构重构阶段 0：现状基线

> 记录日期：2026-08-29
>
> 分支：`codex/modular-assessment-refactor`
>
> 目的：为渐进式重构建立可回归的运行与功能基线；本阶段不改变用户功能。

## 启动基线

统一启动配置位于 `scripts/服务配置.psd1`，当前包含 10 个本地进程：

| 进程 | 端口 | 当前入口 |
|---|---:|---|
| 整合平台 | 4173 | `npm run start` |
| 统一账号与证据中心 | 8020 | `modules/platform-core/main.py` |
| 报告生成服务 | 8030 | `modules/report-agent/main.py` |
| 聊天观察 | 3000 | `modules/chat/app.js` |
| 故事共创后端 | 8010 | FastAPI |
| 故事共创前端 | 5174 | Vite |
| 深海基地后端 | 8005 | FastAPI |
| 深海基地前端 | 3001 | Vite |
| 职业模拟器 | 8000 | FastAPI/Jinja |
| 天赋报告 | 5175 | Vite/Vue |

## 功能回归基线

重构期间必须持续保留以下最短路径：

1. 平台账号注册、登录和退出；
2. 从探索星球进入聊天、故事、深海和职业模块；
3. 各模块能通过现有桥接脚本上报证据；
4. 我的作品、成长足迹和天赋报告可以读取既有数据；
5. `一键启动.ps1`、`检查服务状态.ps1` 与 `停止全部服务.ps1` 保持可用。

## 自动检查基线

根目录 `npm test` 依次执行：

- `npm run build`；
- 页面与探索数据 Node 测试；
- 启动服务注册表 PowerShell 测试；
- `modules/platform-core` 的 Python 单元测试。

后续阶段新增的契约或 Core API 行为，必须增加相应测试，不得以替换旧测试的方式降低此基线。

## 数据保护

- `modules/platform-core/data/ai_bole_core.db` 视为既有数据，不随本重构分支提交；
- 架构迁移开始前先以 SQLite 一致性备份方式复制数据库；
- 模块自有数据库和聊天数据目录在其模块接入阶段前保持只读来源。
