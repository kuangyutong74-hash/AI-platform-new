"""AI伯乐报告生成智能体（可替换模型的演示服务）。"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any
from fastapi import FastAPI
from pydantic import BaseModel, Field

INTELLIGENCE_NAMES = {"linguistic":"语言智能", "logical_mathematical":"逻辑—数学智能", "spatial":"空间智能", "interpersonal":"人际智能", "intrapersonal":"内省智能", "naturalistic":"自然观察智能"}

class EvidenceEvent(BaseModel):
    id: str | None = None
    module: str
    event_type: str
    occurred_at: str
    evidence_level: str = "reference"
    intelligence_candidates: list[str] = Field(default_factory=list)
    behavior_summary: str
    raw_evidence: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)

class ReportRequest(BaseModel):
    child_name: str = "小朋友"
    events: list[EvidenceEvent] = Field(default_factory=list)

app = FastAPI(title="AI伯乐报告生成智能体", version="0.1.0")

def build_report(request: ReportRequest) -> dict[str, Any]:
    """只使用已采集证据生成叙述，不推断未出现的能力。"""
    grouped: dict[str, list[EvidenceEvent]] = defaultdict(list)
    for event in request.events:
        for key in event.intelligence_candidates:
            if key in INTELLIGENCE_NAMES:
                grouped[key].append(event)
    dimensions = []
    for key, name in INTELLIGENCE_NAMES.items():
        items = grouped.get(key, [])
        strong = sum(item.evidence_level == "strong" for item in items)
        modules = sorted({item.module for item in items})
        status = "采集行为较少" if len(items) < 2 else ("证据丰富" if strong >= 2 else "证据均衡")
        refs = [item.id for item in items if item.id]
        if items:
            lead = "；".join(item.behavior_summary for item in items[:2])
            analysis = f"在{'、'.join(modules)}中观察到：{lead}。这些记录只用于描述本阶段出现过的行为线索。"
        else:
            analysis = "本阶段暂未收集到该维度的可回溯行为线索，不能据此判断孩子是否具备或缺少相关能力。"
        dimensions.append({"key": key, "name": name, "status": status, "evidence_refs": refs, "analysis": analysis})
    module_counts = Counter(event.module for event in request.events)
    active = [name for name, count in module_counts.items() if count]
    cross = f"本阶段在{'、'.join(active) or '四个活动模块'}中留下了可回溯记录。建议结合不同情境继续观察，而不是依据单次行为下结论。"
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "rule": "只统计行为频次、类型和原始上下文，不换算能力分数，不输出排名。", "dimensions": dimensions, "cross_insights": [{"text": cross, "evidence_refs": [e.id for e in request.events[:3] if e.id]}], "recommendations": {"family": "围绕已出现的行为安排低压力延伸活动，并邀请孩子解释自己的选择或修改过程。", "classroom": "保留作品版本、策略变化和协作对话，让后续观察可以回到具体证据。"}}

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "report-agent"}

@app.post("/api/report/generate")
def generate_report(request: ReportRequest) -> dict[str, Any]:
    return build_report(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8030, reload=False)
