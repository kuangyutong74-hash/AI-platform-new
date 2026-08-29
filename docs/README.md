# AI 伯乐文档总览

这里是项目技术文档的统一入口。新伙伴建议按“先运行、再理解边界、最后修改契约”的顺序阅读。

## 推荐阅读顺序

1. [根 README](../README.md)：完成安装、模型配置、启动和基础验证。
2. [开发与交接指南](development-and-handover.md)：理解服务拓扑、数据流、常见故障和提交要求。
3. [架构设计 v1.1](superpowers/specs/2026-08-29-modular-assessment-platform-architecture-design.md)：理解重构决策、目标模型和 API 边界。
4. [重构实施状态](modular-assessment-refactor-status.md)：确认已完成阶段、发布边界与仍保留的兼容路径。
5. [行为证据埋点清单](行为证据采集埋点清单.md)：修改模块事件或报告逻辑前必读。

## 文档地图

| 文档 | 面向读者 | 解决的问题 |
| --- | --- | --- |
| [开发与交接指南](development-and-handover.md) | 开发、维护、测试人员 | 如何配置、调试、扩展、迁移和发布 |
| [架构设计 v1.1](superpowers/specs/2026-08-29-modular-assessment-platform-architecture-design.md) | 架构与后端开发 | 为什么采用 Portal + Core + SDK + Module，数据归谁管理 |
| [阶段 0 基线](architecture/phase-0-baseline.md) | 维护旧链路的开发者 | 重构前有哪些功能和数据来源，哪些不能遗漏 |
| [重构实施状态](modular-assessment-refactor-status.md) | 项目负责人 | 阶段 0–5 完成度、验证命令与发布边界 |
| [行为证据埋点清单](行为证据采集埋点清单.md) | 模块与报告开发 | 每个事件采什么、映射哪些观察维度、证据强度如何定义 |
| [Core OpenAPI](../packages/contracts/openapi/core-api.v1.yaml) | 前后端与 SDK 开发 | V1 请求、响应和错误的机器可读契约 |
| [JSON Schema](../packages/contracts/schemas) | 模块开发 | Manifest、Envelope、事件和作品的机器校验规则 |

## 文档维护规则

- 行为改变时同步更新代码、契约、测试和对应文档。
- 服务端口与启动命令以 `scripts/服务配置.psd1` 为准。
- API 以 OpenAPI 和 JSON Schema 为准；架构文档解释原因，不复制一套容易漂移的字段定义。
- 文档示例只能使用占位密钥，不记录真实学生数据、账号或本地数据库内容。
- 已实现状态与目标设计分开记录：设计放在架构文档，实际完成度放在实施状态文档。
