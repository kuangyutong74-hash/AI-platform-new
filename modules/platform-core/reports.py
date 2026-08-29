"""Core 内置的可解释报告规则；不把行为记录转换为能力分数或排名。"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any


DIMENSIONS = {
    "linguistic": "语言智能", "logical": "逻辑—数学智能", "spatial": "空间智能",
    "interpersonal": "人际智能", "intrapersonal": "内省智能", "naturalistic": "自然观察智能",
}
MODULE_NAMES = {"chat": "聊天观察", "story": "故事共创", "deep_sea": "深海基地重建", "career": "职业模拟器"}
SYNONYMS = {"logical_mathematical": "logical"}
RULE = "只复述已采集的行为线索，不换算能力分数、等级或排名。"


def _key(value: str) -> str | None:
    value = SYNONYMS.get(value, value)
    return value if value in DIMENSIONS else None


def generate_internal_report(child_name: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        for candidate in event.get("intelligence_candidates", []):
            key = _key(str(candidate))
            if key:
                grouped[key].append(event)
    dimensions = []
    for key, name in DIMENSIONS.items():
        items = grouped.get(key, [])
        refs = list(dict.fromkeys(str(item.get("id")) for item in items if item.get("id")))
        modules = "、".join(sorted({MODULE_NAMES.get(str(item.get("module")), str(item.get("module"))) for item in items}))
        strong = sum(item.get("evidence_level") == "strong" for item in items)
        if items:
            examples = "；".join(str(item.get("behavior_summary", "")).rstrip("。；") for item in items[:4])
            analysis = f"本阶段在{modules}中收集到 {len(items)} 条可回溯行为记录，其中 {strong} 条为较完整记录。观察到：{examples}。这些记录反映的是孩子在当前情境中的做法，后续仍应在不同任务中继续观察其是否会主动重复、解释并调整这些方法。"
            adult = f"可以继续留意孩子在新任务里是否会再次出现“{str(items[0].get('behavior_summary', '')).rstrip('。')}”这样的做法，并邀请他说明原因。"
            child = f"你在{MODULE_NAMES.get(str(items[0].get('module')), '探索活动')}里留下了一次真实的小发现：{str(items[0].get('behavior_summary', '')).rstrip('。')}。"
        else:
            analysis = "本阶段暂未收集到可回溯行为线索，因此不作判断。完成相关探索后，这里会结合真实行为生成观察提示。"
            adult = "暂无可观测数据。完成相关探索后，这里会结合孩子的真实行为生成观察提示。"
            child = "还没有可回看的探索记录。完成一次相关探索后，我会把你的真实表现写在这里。"
        dimensions.append({"key": key, "name": name, "status": "采集行为较少" if len(items) < 2 else ("证据丰富" if strong >= 2 else "证据均衡"), "evidence_refs": refs, "analysis": analysis, "adult_observation": adult, "child_story": child})
    refs = [str(event["id"]) for event in events if event.get("id")]
    active = "、".join(MODULE_NAMES.get(module, module) for module in Counter(str(event.get("module")) for event in events)) or "活动模块"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(), "rule": RULE, "dimensions": dimensions,
        "cross_insights": [{"text": f"{child_name}在{active}中留下了可回溯记录。建议在不同情境中继续观察，不依据单次行为下结论。", "evidence_refs": refs[:3]}],
        "evidence_explanations": [{"evidence_ref": event.get("id"), "title": MODULE_NAMES.get(str(event.get("module")), "探索过程回顾"), "summary": event.get("behavior_summary", ""), "details": ["系统保留了这次活动中的关键行为过程，供家长和老师后续对照观察。"]} for event in events],
        "recommendations": {"family": ["请孩子讲讲自己先做了什么、后来为什么改变。", "把体验变成低压力小游戏，允许先试再改。"], "teacher": ["记录孩子的第一种方案、反馈后的调整和最终结果。", "隔一至两周在新情境中复现相似任务。"]},
    }
