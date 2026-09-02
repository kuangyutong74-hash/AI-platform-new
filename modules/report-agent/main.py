"""AI伯乐报告智能体：规则兜底 + OpenAI-compatible 可插拔分析器。"""
from __future__ import annotations

import json
import logging
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
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
    "chat.observation-shared.v1": "自由表达与交流",
    "story.contribution-completed.v1": "故事创作与完成",
    "deep-sea.spatial-task-completed.v1": "深海基地任务",
    "deep-sea.session-completed.v1": "深海基地完整重建",
    "career.task-completed.v1": "职业任务体验",
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
PLATFORM_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
logger = logging.getLogger("report-agent")


def platform_env() -> dict[str, str]:
    """读取平台根目录的本地配置；进程环境变量始终拥有更高优先级。"""
    if not PLATFORM_ENV_PATH.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in PLATFORM_ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


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
    if event.event_type == "chat.observation-shared.v1":
        details = [
            f"孩子共进行了 {raw.get('turnCount', 0)} 轮表达。",
            "系统按会话保存了交流过程；只有带轮次编号的内容才能判断属于哪一轮。",
        ]
        summary = event.context.get("sessionSummary", {}) if isinstance(event.context, dict) else {}
        words = str(summary.get("childWords", "")).strip()
        if words:
            details.append(f"孩子的真实表达摘录：“{words[:100]}”")
    elif event.event_type == "career.task-completed.v1":
        details = [
            f"过程中主动尝试 {raw.get('attemptCount', 0)} 次，并调整 {raw.get('adjustmentCount', 0)} 次。",
            f"遇到困难时查看提示 {raw.get('hintCount', 0)} 次，用时约 {raw.get('completionSeconds', 0)} 秒。",
        ]
    elif event.event_type == "deep-sea.spatial-task-completed.v1":
        details = [
            f"完成第 {raw.get('level', 0)} 个深海任务，用时约 {raw.get('completionSeconds', 0)} 秒。",
            f"根据反馈调整了 {raw.get('adjustmentCount', 0)} 次。",
        ]
    elif event.event_type == "deep-sea.session-completed.v1":
        details = [f"完成 {raw.get('completedLevels', 0)} / {raw.get('totalLevels', 0)} 个深海任务。", f"总用时约 {raw.get('completionSeconds', 0)} 秒，调整 {raw.get('adjustmentCount', 0)} 次。"]
    elif event.event_type == "story.contribution-completed.v1":
        details = [f"本次贡献了 {raw.get('contributionCount', 0)} 个故事片段。", f"故事《{raw.get('storyTitle', '故事共创')}》已完成并保存。"]
    if not details:
        details = ["系统保留了这次活动中的关键行为过程，供家长和老师后续对照观察。"]
    return {
        "evidence_ref": event.id,
        "title": EVENT_NAMES.get(event.event_type, "探索过程回顾"),
        "summary": event.behavior_summary,
        "details": details,
    }


def child_story_for_event(event: EvidenceEvent) -> str:
    """只用这一局真实记录写儿童回顾；即使模型不可用也不退回预设宣传语。"""
    raw = event.raw_evidence
    summary = event.context.get("sessionSummary", {}) if isinstance(event.context, dict) else {}
    artifacts = event.context.get("artifacts", []) if isinstance(event.context, dict) else []
    artifact = next((item for item in artifacts if isinstance(item, dict) and item.get("title")), {})
    title = str(artifact.get("title", "")).strip()
    artifact_summary = str(artifact.get("summary", "")).strip()
    if event.module == "chat":
        words = str(summary.get("childWords", "")).strip()
        topic = str(raw.get("topicKey", "")).strip() or title
        if words:
            if topic:
                return f"这次聊天进入时选择了“{topic}”主题；在会话中的另一段表达里，你提到：{words[:80]}。现有记录没有把这两段内容标为同一轮。"
            return f"这次聊天中，你有一段真实表达：{words[:80]}。"
        if topic:
            return f"这次聊天里，你围绕“{topic}”进行了 {raw.get('turnCount', 0)} 轮表达。智能体只记录了这次真实聊过的内容。"
    if event.module == "story" and title:
        detail = artifact_summary or f"你为故事贡献了 {raw.get('contributionCount', 0)} 个片段"
        return f"在《{title}》的共创里，{detail.rstrip('。')}。这是这次故事游戏留下的真实记录。"
    if event.module == "deep_sea":
        if int(raw.get("level", 0)) == 1:
            successful = int(raw.get("successfulPairs", 0))
            total = int(raw.get("totalPairs", 4))
            accuracy = round(float(raw.get("accuracyPercent", successful / max(total, 1) * 100)))
            checks = raw.get("checkAttempts")
            check_text = f"，一共检查了 {checks} 次" if checks is not None else ""
            result = "全部配对成功" if successful == total else "还没有全部配对成功"
            return f"第一关生物配对中，你成功配对了 {successful}/{total} 组，最终准确度 {accuracy}%（{result}）{check_text}。"
        return f"在深海任务中，你完成了 {raw.get('completedLevels', raw.get('level', 0))} 个关卡，并根据反馈调整了 {raw.get('adjustmentCount', 0)} 次。"
    if event.module == "career":
        task = str(raw.get("taskKey", "这次职业任务")).strip()
        return f"在“{task}”职业任务里，你尝试了 {raw.get('attemptCount', 0)} 次，并调整了 {raw.get('adjustmentCount', 0)} 次选择。"
    if artifact_summary:
        return f"这次探索留下的真实记录是：{artifact_summary}"
    return "这次体验已经完成，但目前保存的记录还不足以写出这颗星的专属发现。"


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
                f"具体记录：{'；'.join(child_story_for_event(item).rstrip('。；') for item in items[:4])}。"
                f"本阶段在{'、'.join(modules)}中共留下{len(items)}条相关过程记录，其中{strong}条较完整。"
                "这些内容只说明孩子在当时任务里采用了哪些做法，不等同于固定能力结论。"
                if items else "本阶段暂未收集到该维度的可回溯行为线索，因此不作判断。"
            )
            observation = (
                "换一个相似但不完全相同的任务，观察孩子是否会主动沿用这次的方法；"
                "请孩子讲一讲为什么这样选择，留意他能否说清判断依据；"
                "遇到结果不理想时，观察孩子会先检查哪里、怎样调整，以及是否愿意再次尝试；"
                "隔一至两周在家庭或课堂的新情境中再次观察，比较这种做法是否会自然出现。"
                if items else "暂无可观测数据。完成相关探索后，这里会结合孩子的真实行为生成观察提示。"
            )
            child_story = child_story_for_event(items[0]) if items else "还没有可回看的探索记录。去对应的大陆完成一次游戏后，我会根据那一局的真实内容写在这里。"
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
raw_evidence 与 context 描述已经出现的行为线索。context 中的 sessionSummary 和 artifacts 是该局真实游戏内容，应优先用于生成具体描述。
聊天事件中，topicKey 只是进入会话时选择的入口主题，sessionSummary.childWords 是整场会话汇总摘录；除非输入提供明确的逐轮对应关系，
严禁写成“孩子围绕 topicKey 说了 childWords”，必须分开描述为“入口主题”和“会话中另一段表达”，也不得据此推断两者的因果或语义关系。
如果 raw_evidence.childTurns 存在，只能按其中的 turn 与 text 逐轮引用，不得把不同 turn 的内容合并成一句话或同一个观点。
六个维度必须遵守不同的分析边界：
- interpersonal（人际智能）：只分析孩子如何提到、理解、回应他人，以及合作、协商、关系期待；不能把“我开心”等自我感受本身当成人际结论。
- intrapersonal（内省智能）：只分析孩子是否命名自己的感受、偏好、动机、不确定或自我调整；不能把“提到同学”本身当成内省结论。
- linguistic（语言智能）：只分析真实表达的组织、词语、因果、叙事和修改过程。
- logical（逻辑智能）：只分析比较、规则、因果推理、检查与策略调整。
- spatial（空间智能）：只分析位置、方向、旋转、布局和空间建构。
- naturalistic（自然观察智能）：只分析生物差异、分类、生态关系和观察依据。
同一事件可以支持多个维度，但各维度 analysis 和 adult_observation 必须回答各自不同的问题；除输入中的同一句真实引语外，
interpersonal 与 intrapersonal 不得复用相同句子、结论或观察建议。证据不足时应明确写“本次只观察到……，尚不足以说明……”。
不得推断未出现的能力，不得输出能力分数、等级或排名。每个维度 analysis 是左页的“本次具体表现”，必须优先写事实：
真实故事名、话题、任务名、孩子原话（仅限输入中存在的原话）、完成次数、用时、尝试/调整/提示次数及先后过程；不得在 analysis
中写家庭建议或“后续可观察”，不得为凑长度重复或虚构。每条
对于 chat、story 等语言相关事件，只要 context.sessionSummary、raw_evidence.childTurns 或 artifacts 中存在孩子原话，analysis 必须选取
一段最相关的短原话，用中文引号“……”逐字引用；不得润色、补全或把系统摘要伪装成引语。
cross_insights 必须引用输入中真实存在的 evidence_refs，但正文绝不显示 id。模块必须写中文：chat=聊天观察、story=故事共创、
deep_sea=深海基地重建、career=职业模拟器。family 和 teacher 各返回4至6条不同的可执行建议数组，不得在建议中写记录 id。
logical_mathematical 归一化为 logical。
每个维度还要返回 adult_observation：这是右页的“迁移观察清单”，不得复述 analysis。请给出3至5个彼此不同、可执行的观察方向，
覆盖新情境迁移、理由表达、受挫后的调整、合作方式或一至两周后的复现；各项用“；”分隔，不得对孩子下结论。没有记录时固定返回
“暂无可观测数据。完成相关探索后，这里会结合孩子的真实行为生成观察提示。”。每个维度还要返回 child_story：面向孩子，
用第二人称和一至两句儿童能读懂的话，只复述该维度已有的真实游戏表现，尽量点明真实话题、故事名、任务名、孩子原话或实际调整次数。
不得套用示例、虚构引语或泛泛夸奖，也不得因为事件被标记为某维度就虚构该维度行为（例如聊天记录没有自然观察内容时，不能写成观察了自然）；没有记录时说明
还没有可回看的探索记录。另外返回 evidence_explanations 数组，
每条包含 evidence_ref、中文 title、自然语言 summary 和 2 至 4 条 details；只能解释已有数据，不显示事件代码、字段名、
会话编号或图片地址。

必须只返回一个 JSON 对象（不要 Markdown 代码块、说明文字或额外顶层字段），并严格使用下面的嵌套结构：
{
  "dimensions": [
    {
      "key": "linguistic | logical | spatial | interpersonal | intrapersonal | naturalistic",
      "status": "证据丰富 | 证据均衡 | 采集行为较少",
      "evidence_refs": ["输入事件中真实存在的 id"],
      "analysis": "...",
      "adult_observation": "...",
      "child_story": "..."
    }
  ],
  "cross_insights": [
    {"text": "...", "evidence_refs": ["输入事件中真实存在的 id"]}
  ],
  "evidence_explanations": [
    {
      "evidence_ref": "输入事件中真实存在的 id",
      "title": "...",
      "summary": "...",
      "details": ["...", "..."]
    }
  ],
  "recommendations": {
    "family": ["..."],
    "teacher": ["..."]
  }
}
dimensions 必须恰好包含上述六个 key，每个 key 各一次；即使没有对应证据也必须保留该维度并使用空 evidence_refs。
不得把 linguistic、logical_mathematical、family 或 teacher 放在顶层；family 与 teacher 只能位于 recommendations 内。
不得返回 generated_at 或 rule，这两个字段由服务端生成。"""


class LLMAnalyzer:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url, self.api_key, self.model = base_url.rstrip("/"), api_key, model

    @classmethod
    def from_environment(cls) -> "LLMAnalyzer | None":
        local = platform_env()
        base_url = os.getenv("REPORT_LLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or local.get("REPORT_LLM_BASE_URL") or local.get("DEEPSEEK_BASE_URL", "")
        api_key = os.getenv("REPORT_LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or local.get("REPORT_LLM_API_KEY") or local.get("DEEPSEEK_API_KEY", "")
        model = os.getenv("REPORT_LLM_MODEL") or os.getenv("DEEPSEEK_MODEL") or local.get("REPORT_LLM_MODEL") or local.get("DEEPSEEK_MODEL", "")
        values = [str(value).strip() for value in (base_url, api_key, model)]
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

    def expand_dimensions(self, events: list[EvidenceEvent], report: dict[str, Any]) -> dict[str, Any]:
        """第二阶段只负责把六个维度写深，避免完整报告任务挤压维度内容。"""
        endpoint = self.base_url if self.base_url.endswith("/chat/completions") else f"{self.base_url}/chat/completions"
        system = """你是儿童行为报告的维度深描智能体。只依据输入 events 扩写 dimensions，不得添加新事实、分数、等级或诊断。
每个有 evidence_refs 的维度必须返回：
每个有证据维度必须返回 facts（2至4条具体事实）、interpretations（2至4条本维度解释）、limits（1至2条证据边界）和 adult_observations（恰好4条）。
facts 必须引用真实任务名、数值或一小段输入中确实存在的孩子原话；interpretations 只讨论该维度；limits 明确本次尚不能说明什么。
adult_observations 每条25至60个中文字符，依次覆盖①新情境迁移、②理由或感受表达、③遇到困难后的调整、④一至两周后的复现。
interpersonal 只写理解/回应他人、合作、关系互动；intrapersonal 只写自我感受、偏好、动机、自我调节。两者即使引用同一句原话，也不得复用相同解释、结论和观察任务。
聊天的 topicKey 是入口主题，不能与 sessionSummary.childWords 合并为同一轮；没有 childTurns 时不得建立二者关系。引语必须逐字来自输入。
无证据维度使用空数组。只返回 JSON：{\"dimensions\":[{\"key\":\"...\",\"facts\":[\"...\"],\"interpretations\":[\"...\"],\"limits\":[\"...\"],\"adult_observations\":[\"...\",\"...\",\"...\",\"...\"]}]}，六个 key 各一次。"""
        payload = {
            "model": self.model, "temperature": 0.15, "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps({"events": [event.model_dump() for event in events], "dimensions": report.get("dimensions", [])}, ensure_ascii=False)},
            ],
        }
        http_request = urlrequest.Request(endpoint, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlrequest.urlopen(http_request, timeout=45) as response:
                result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            return json.loads(str(content).strip().removeprefix("```json").removesuffix("```").strip())
        except (error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("维度深描模型请求失败") from exc


def apply_dimension_expansion(report: dict[str, Any], expansion: dict[str, Any]) -> dict[str, Any]:
    supplied = {canonical_key(str(item.get("key", ""))): item for item in expansion.get("dimensions", []) if isinstance(item, dict)}
    for dimension in report.get("dimensions", []):
        item = supplied.get(dimension.get("key"))
        if not item or not dimension.get("evidence_refs"):
            continue
        clean_list = lambda value: [str(part).strip().rstrip("。；;，,") for part in value if str(part).strip()] if isinstance(value, list) else []
        facts = clean_list(item.get("facts"))[:4]
        interpretations = clean_list(item.get("interpretations"))[:4]
        limits = clean_list(item.get("limits"))[:2]
        observation_items = clean_list(item.get("adult_observations"))
        if facts and interpretations and limits:
            dimension["analysis"] = (
                f"具体表现：{'；'.join(facts)}。"
                f"本维度观察：{'；'.join(interpretations)}。"
                f"证据边界：{'；'.join(limits)}。"
            )
        if len(observation_items) >= 4:
            dimension["adult_observation"] = "；".join(observation_items[:4])
    return report


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
            report = normalize_report(analyzer.analyze(report_request.events), report_request.events)
        except (RuntimeError, KeyError, IndexError, TypeError, ValueError):
            logger.exception("第一阶段报告生成失败，改用规则报告")
            return RuleAnalyzer().analyze(report_request.events)
        try:
            return apply_dimension_expansion(report, analyzer.expand_dimensions(report_request.events, report))
        except (RuntimeError, KeyError, IndexError, TypeError, ValueError):
            logger.exception("第二阶段维度深描失败，暂时返回第一阶段报告")
            return report
    return RuleAnalyzer().analyze(report_request.events)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8030, reload=False)
