# AI伯乐报告生成智能体

```text
四模块行为事件 → 证据去重/归类 → 六类智能维度 → 可回溯表述 → 家庭/课堂建议
```

`POST /api/report/generate` 接收平台事件，默认使用本地规则生成，后续可替换为企业模型或 OpenAI-compatible API。设计约束：不根据行为换算能力分数、不输出排名，每个结论保留 `evidence_refs`。

如需启用 OpenAI-compatible 分析路径，同时配置 `REPORT_LLM_BASE_URL`、`REPORT_LLM_API_KEY`和 `REPORT_LLM_MODEL`。任一项缺失或请求失败时都会自动回退到本地规则；两条路径输出同一 JSON 结构。
