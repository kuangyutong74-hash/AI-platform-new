"""AI伯乐报告智能体：规则兜底 + OpenAI-compatible 可插拔分析器。"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any
from urllib import error, request as urlrequest

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

CANONICAL = {"linguistic", "logical", "spatial", "interpersonal", "intrapersonal", "naturalistic"}
SYNONYMS = {"logical_mathematical": "logical"}
INTELLIGENCE_NAMES = {
    "linguistic": "语言智能", "logical": "逻辑—数学智能", "spatial": "空间智能",
    "interpersonal": "人际智能", "intrapersonal": "内省智能", "naturalistic": "自然观察智能",
}
MODULE_NAMES = {"chat": "聊天观察", "story": "故事共创", "deep_sea": "深海基地重建", "career": "职业模拟器"}
EVENT_NAMES = {
    "narrative_evidence": "自由表达与交流",
    "story_contribution": "故事创作与完成",
    "story_revision": "故事修改与完善",
    "ecology_strategy": "生态线索配对",
    "spatial_solution": "能源线路搭建",
    "mediation_response": "角色分歧协调",
    "workday_process_summary": "职业任务体验",
    "decision_revision": "方案判断与调整",
}
REPORT_RULE = "只统计行为频次、类型和原始上下文，不换算能力分数，不输出排名。"


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


def canonical_key(key: str) -> str | None:
    normalized = SYNONYMS.get(key, key)
    return normalized if normalized in CANONICAL else None


def event_refs(events: list[EvidenceEvent]) -> list[str]:
    return list(dict.fromkeys(event.id for event in events if event.id))


def explain_event(event: EvidenceEvent) -> dict[str, Any]:
    """把机器采集字段转换为成人可以直接阅读的过程回顾。"""
    raw = event.raw_evidence
    details: list[str] = []
    if event.event_type == "narrative_evidence":
        details = [
            f"孩子共进行了 {raw.get('turn_count', 0)} 轮表达。",
            f"其中有 {raw.get('long_turn_count', 0)} 次较完整的连续表达。",
            f"孩子主动表达的文字约 {raw.get('total_child_chars', 0)} 个字。",
        ]
    elif event.event_type == "workday_process_summary":
        details = [
            f"完成了 {raw.get('completed_stages', 0)} 个职业任务阶段。",
            f"过程中主动尝试 {raw.get('interaction_count', 0)} 次，并调整或重试 {int(raw.get('adjustment_count', 0) or 0) + int(raw.get('retry_count', 0) or 0)} 次。",
            f"遇到困难时查看提示 {raw.get('hint_count', 0)} 次。",
        ]
    elif event.event_type == "spatial_solution":
        details = [
            f"搭建过程中旋转或调整管件 {raw.get('rotate_count', 0)} 次。",
            "最终完成了线路连通。" if raw.get("connected") else "本次尚未完成线路连通，仍保留了尝试过程。",
        ]
    elif event.event_type == "ecology_strategy":
        details = [
            f"成功完成 {raw.get('successful_pairs', 0)} 组生态配对。",
            f"根据反馈重新调整了 {raw.get('meaningful_adjustments', 0)} 次判断。",
        ]
    elif event.event_type == "mediation_response":
        details = ["孩子在角色分歧中尝试理解双方需要，并选择了支持协商的回应。"]
    elif event.event_type == "story_contribution":
        details = [f"孩子独立完成了约 {raw.get('ending_length', 0)} 字的故事结尾。", "本次故事已经完整收尾并保存。"]
    if not details:
        details = ["系统保留了这次活动中的关键行为过程，供家长和老师后续对照观察。"]
    return {
        "evidence_ref": event.id,
        "title": EVENT_NAMES.get(event.event_type, "探索过程回顾"),
        "summary": event.behavior_summary,
        "details": details,
    }


class RuleAnalyzer:
    """只复述已经出现的行为线索，不推断未采集内容。"""

    def analyze(self, events: list[EvidenceEvent]) -> dict[str, Any]:
        grouped: dict[str, list[EvidenceEvent]] = defaultdict(list)
        for event in events:
            for candidate in event.intelligence_candidates:
                key = canonical_key(candidate)
                if key:
                    grouped[key].append(event)
        dimensions = []
        for key, name in INTELLIGENCE_NAMES.items():
            items = grouped.get(key, [])
            strong = sum(item.evidence_level == "strong" for item in items)
            modules = sorted({MODULE_NAMES.get(item.module, item.module) for item in items})
            status = "采集行为较少" if len(items) < 2 else ("证据丰富" if strong >= 2 else "证据均衡")
            refs = event_refs(items)
            analysis = (
                f"本阶段在{'、'.join(modules)}中收集到{len(items)}条相关行为记录，其中{strong}条为较完整记录。"
                f"具体表现为：{'；'.join(item.behavior_summary.rstrip('。；') for item in items[:4])}。"
                "这些行为说明孩子在当前任务里已经尝试调用这一类方法，但它们反映的是具体情境中的表现，不等同于固定能力结论。"
                "后续可继续观察孩子能否在不同任务中主动重复这种方法，以及遇到困难时会怎样解释、调整和再次尝试。"
                if items else "本阶段暂未收集到该维度的可回溯行为线索，因此不作判断。"
            )
            observation = (
                f"在{name}方面，可以继续留意孩子在新的任务里是否会再次出现“{items[0].behavior_summary.rstrip('。')}”这样的做法，"
                "以及他能否说出为什么这样选择、遇到变化后如何调整。"
                if items else "暂无可观测数据。完成相关探索后，这里会结合孩子的真实行为生成观察提示。"
            )
            child_story = (
                f"在{MODULE_NAMES.get(items[0].module, items[0].module)}里，{items[0].behavior_summary.rstrip('。')}。"
                "这是你这次探索留下的真实小发现。"
                if items else "还没有可回看的探索记录。去对应的大陆完成一次游戏后，我会把你的真实表现写在这里。"
            )
            dimensions.append({"key": key, "name": name, "status": status, "evidence_refs": refs, "analysis": analysis, "adult_observation": observation, "child_story": child_story})
        active = [MODULE_NAMES.get(name, name) for name, count in Counter(event.module for event in events).items() if count]
        refs = event_refs(events)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(), "rule": REPORT_RULE,
            "dimensions": dimensions,
            "cross_insights": [{
                "text": f"本阶段在{'、'.join(active) or '活动模块'}中留下了可回溯记录。建议结合不同情境继续观察，不依据单次行为下结论。",
                "evidence_refs": refs[:3],
            }],
            "evidence_explanations": [explain_event(event) for event in events],
            "recommendations": {
                "family": [
                    "每天留出十分钟，请孩子挑一个今天最投入的环节，讲讲自己先做了什么、后来为什么改变。",
                    "把体验中的任务变成低压力家庭小游戏，允许孩子先试、再改，不急着给标准答案。",
                    "用照片或小卡片保存孩子的作品版本和关键表达，一周后一起回看方法发生了什么变化。",
                    "当孩子卡住时，多问“你发现了什么”“下一次想换哪种办法”，帮助他把思考过程说出来。",
                ],
                "teacher": [
                    "在课堂任务中同时提供口头表达、绘画建构和角色协作等入口，观察孩子更自然地选择哪种方式。",
                    "记录孩子第一次方案、收到反馈后的调整和最终结果，重点关注方法变化而不只看答案。",
                    "安排不同角色和同伴组合，继续观察孩子如何表达需要、理解他人并协调分歧。",
                    "隔一至两周在新情境中复现相似任务，确认行为线索是否能够跨情境稳定出现。",
                ],
            },
        }


SYSTEM_PROMPT = """你是儿童阶段性行为报告助手。只能依据输入 events 中的 behavior_summary、intelligence_candidates、
raw_evidence 与 context 描述已经出现的行为线索，不得推断未出现的能力，不得输出能力分数、等级或排名。每个维度 analysis
须结合2至4条具体行为，写清楚“观察到什么—可能反映何种当前策略—还需继续观察什么”，不少于120字；每条
cross_insights 必须引用输入中真实存在的 evidence_refs，但正文绝不显示 id。模块必须写中文：chat=聊天观察、story=故事共创、
deep_sea=深海基地重建、career=职业模拟器。family 和 teacher 各返回4至6条不同的可执行建议数组，不得在建议中写记录 id。
logical_mathematical 归一化为 logical。
每个维度还要返回 adult_observation：根据该维度真实行为生成一条具体、不同的成人观察提示；没有记录时固定返回
“暂无可观测数据。完成相关探索后，这里会结合孩子的真实行为生成观察提示。”。每个维度还要返回 child_story：面向孩子，
用第二人称和一至两句儿童能读懂的话，只复述该维度已有的真实游戏表现，不得套用示例、虚构引语或泛泛夸奖；没有记录时说明
还没有可回看的探索记录。另外返回 evidence_explanations 数组，
每条包含 evidence_ref、中文 title、自然语言 summary 和 2 至 4 条 details；只能解释已有数据，不显示事件代码、字段名、
会话编号或图片地址。只返回符合约定结构的 JSON。"""


class LLMAnalyzer:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url, self.api_key, self.model = base_url.rstrip("/"), api_key, model

    @classmethod
    def from_environment(cls) -> "LLMAnalyzer | None":
        values = [os.getenv(name, "").strip() for name in ("REPORT_LLM_BASE_URL", "REPORT_LLM_API_KEY", "REPORT_LLM_MODEL")]
        return cls(*values) if all(values) else None

    def analyze(self, events: list[EvidenceEvent]) -> dict[str, Any]:
        endpoint = self.base_url if self.base_url.endswith("/chat/completions") else f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model, "temperature": 0.2, "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"events": [event.model_dump() for event in events]}, ensure_ascii=False)},
            ],
        }
        http_request = urlrequest.Request(endpoint, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlrequest.urlopen(http_request, timeout=45) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("报告模型请求失败") from exc
        content = result["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return json.loads(str(content).strip().removeprefix("```json").removesuffix("```").strip())


def normalize_report(candidate: dict[str, Any], events: list[EvidenceEvent]) -> dict[str, Any]:
    """锁定两条分析路径的结构，并阻止模型伪造证据引用。"""
    fallback = RuleAnalyzer().analyze(events)
    valid_refs = set(event_refs(events))
    dimensions_by_key = {canonical_key(str(item.get("key", ""))): item for item in candidate.get("dimensions", []) if isinstance(item, dict)}
    dimensions = []
    for fallback_item in fallback["dimensions"]:
        item = dimensions_by_key.get(fallback_item["key"])
        if not item:
            dimensions.append(fallback_item)
            continue
        refs = [ref for ref in item.get("evidence_refs", []) if ref in valid_refs]
        dimensions.append({
            "key": fallback_item["key"], "name": fallback_item["name"],
            "status": item.get("status") if item.get("status") in {"证据丰富", "证据均衡", "采集行为较少"} else fallback_item["status"],
            "evidence_refs": refs,
            "analysis": str(item.get("analysis", "")).strip() if refs else fallback_item["analysis"],
            "adult_observation": str(item.get("adult_observation", "")).strip() if refs else fallback_item["adult_observation"],
            "child_story": str(item.get("child_story", "")).strip() if refs else fallback_item["child_story"],
        })
    cross_insights = []
    for item in candidate.get("cross_insights", []):
        if isinstance(item, dict):
            refs = [ref for ref in item.get("evidence_refs", []) if ref in valid_refs]
            text = str(item.get("text", "")).strip()
            if text and refs:
                cross_insights.append({"text": text, "evidence_refs": refs})
    if not cross_insights:
        cross_insights = fallback["cross_insights"]
    explanations_by_ref = {
        str(item.get("evidence_ref")): item for item in candidate.get("evidence_explanations", [])
        if isinstance(item, dict) and str(item.get("evidence_ref")) in valid_refs
    }
    evidence_explanations = []
    for fallback_item in fallback["evidence_explanations"]:
        item = explanations_by_ref.get(str(fallback_item["evidence_ref"]), {})
        details = item.get("details", []) if isinstance(item.get("details"), list) else []
        clean_details = [str(detail).strip() for detail in details if str(detail).strip()]
        evidence_explanations.append({
            "evidence_ref": fallback_item["evidence_ref"],
            "title": str(item.get("title", "")).strip() or fallback_item["title"],
            "summary": str(item.get("summary", "")).strip() or fallback_item["summary"],
            "details": clean_details[:4] or fallback_item["details"],
        })
    supplied = candidate.get("recommendations", {}) if isinstance(candidate.get("recommendations"), dict) else {}
    def advice_list(value: Any, fallback_items: list[str]) -> list[str]:
        values = value if isinstance(value, list) else [value] if isinstance(value, str) else []
        clean = [str(item).strip() for item in values if str(item).strip()]
        return (clean + [item for item in fallback_items if item not in clean])[:6]
    family = advice_list(supplied.get("family"), fallback["recommendations"]["family"])
    teacher = advice_list(supplied.get("teacher"), fallback["recommendations"]["teacher"])
    if teacher == family: teacher = fallback["recommendations"]["teacher"]
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "rule": REPORT_RULE, "dimensions": dimensions, "cross_insights": cross_insights, "evidence_explanations": evidence_explanations, "recommendations": {"family": family, "teacher": teacher}}


app = FastAPI(title="AI伯乐报告生成智能体", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5175"], allow_credentials=True, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "report-agent"}


@app.post("/api/report/generate")
def generate_report(report_request: ReportRequest) -> dict[str, Any]:
    analyzer = LLMAnalyzer.from_environment()
    if analyzer:
        try:
            return normalize_report(analyzer.analyze(report_request.events), report_request.events)
        except (RuntimeError, KeyError, IndexError, TypeError, ValueError):
            pass
    return RuleAnalyzer().analyze(report_request.events)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8030, reload=False)
