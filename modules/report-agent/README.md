# AI伯乐报告生成智能体

```text
四模块行为事件 → 证据去重/归类 → 六类智能维度 → 可回溯表述 → 家庭/课堂建议
```

`POST /api/report/generate` 接收平台事件，默认使用本地规则生成，后续可替换为企业模型或 OpenAI-compatible API。设计约束：不根据行为换算能力分数、不输出排名，每个结论保留 `evidence_refs`。

如需启用 OpenAI-compatible 分析路径，可在平台根目录 `.env` 配置 `DEEPSEEK_BASE_URL`、`DEEPSEEK_API_KEY` 和 `DEEPSEEK_MODEL`。如需给报告服务单独选模型，使用同名的 `REPORT_LLM_*` 变量覆盖。任一项缺失、请求失败或响应无法解析时都会自动回退到本地规则；两条路径输出同一 JSON 结构。

模型响应必须使用嵌套结构：六个维度放在 `dimensions[]`，家庭和教师建议放在 `recommendations.family` 与 `recommendations.teacher`。精确约束由 `SYSTEM_PROMPT` 声明，`normalize_report` 负责过滤伪造的证据引用并补齐缺失内容。修改提示词或字段时必须同时运行 `tests/` 下的报告契约测试。
