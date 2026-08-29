# 模块化评估架构重构：实施状态

基线分支：`codex/modular-assessment-refactor`。本文记录当前可发布实现与原架构规划的对应关系。

| 阶段 | 状态 | 已交付内容 |
| --- | --- | --- |
| 0：基线冻结 | 完成 | 架构现状、模块清单及不迁移边界已纳入原设计文档。 |
| 1：契约与注册 | 完成 | Manifest、JSON Schema、模块目录、OpenAPI 与 Core 校验均已生效。 |
| 2：统一数据库 | 完成 | Core 只保留 V1 会话、授权、源事件、证据、作品与报告表；测试数据通过显式重置工具重建。 |
| 3：Portal 与 Core | 完成 | 作品、足迹、六星资格和报告证据均只读取 V1 接口。 |
| 4：四模块接入 | 完成 | Portal 创建会话后以同页 `window.name` 下发 LaunchContext；四个入口加载 SDK，正常模块事件经 SDK 写入 V1、发布终态作品并完成会话，离开页面时提交 interrupted。 |
| 5：必要收敛 | 完成 | 根工作区集中根平台、Core、模块构建/测试命令；保留各模块既有框架与内部数据。 |

## 发布边界

- V0 旧端点、双写与 bridge 已移除；当前 Core 数据库必须是通过 `reset_dev_data.py --confirm` 创建的纯 V1 数据库。
- 直接进入模块只保留体验与调试，不创建平台正式档案。
- 聊天全文、故事正文和职业内部运行明细仍由所属模块保存；Core 只记录与 session、artifact、source resource 的正式关联。

## 验证命令

```powershell
npm test
npm run verify:workspace
Push-Location modules\platform-core
.\.venv\Scripts\python.exe .\migrate.py --dry-run
Pop-Location
```

`verify:workspace` 已覆盖根平台构建、Core 回归测试、四模块启动入口契约、深海/故事/报告前端构建及聊天模块测试。
