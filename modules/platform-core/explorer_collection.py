"""把统一证据整理成“模块高光”与“账号使用历程”。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


MODULE_COPY = {
    "story": {"island": "想象之洲", "fallback": "想象之洲的新故事", "highlight": "最长故事高光"},
    "deep_sea": {"island": "创造之洲", "fallback": "创造之洲的新设计", "highlight": "最快重建高光"},
    "career": {"island": "未来之洲", "fallback": "未来之洲的新体验", "highlight": "最投入体验高光"},
    "chat": {"island": "倾听之洲", "fallback": "倾听之洲的新发现", "highlight": "最充分表达高光"},
}
MODULE_ORDER = tuple(MODULE_COPY)
DURATION_KEYS = ("duration_seconds", "elapsed_seconds", "duration", "elapsed", "time_spent_seconds")
SCORE_KEYS = ("score", "total_score", "completion_score", "stars")
TURN_KEYS = ("turn_count", "turns", "message_count")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_text(*values: Any) -> str:
    return next((text for value in values if (text := _text(value))), "")


def _raw_context(event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = event.get("raw_evidence") if isinstance(event.get("raw_evidence"), dict) else {}
    context = event.get("context") if isinstance(event.get("context"), dict) else {}
    return raw, context


def _number(event: dict[str, Any], keys: tuple[str, ...]) -> float:
    raw, context = _raw_context(event)
    for source in (raw, context, event):
        for key in keys:
            value = source.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
                return float(value)
    return 0.0


def _content_length(event: dict[str, Any]) -> int:
    raw, context = _raw_context(event)
    explicit = _number(event, ("word_count", "character_count", "content_length"))
    if explicit:
        return int(explicit)
    content = _first_text(
        raw.get("content"), raw.get("story"), raw.get("body"), raw.get("text"), context.get("content")
    )
    return len(content)


def _format_duration(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    minutes, remainder = divmod(total, 60)
    if minutes and remainder:
        return f"{minutes}分{remainder}秒"
    if minutes:
        return f"{minutes}分钟"
    return f"{remainder}秒"


def _event_item(event: dict[str, Any]) -> dict[str, Any]:
    module = event.get("module") if event.get("module") in MODULE_COPY else "chat"
    module_copy = MODULE_COPY[module]
    raw, context = _raw_context(event)
    summary = _first_text(event.get("behavior_summary"), raw.get("summary"), "这里收着一次认真尝试。")
    title = _first_text(raw.get("title"), raw.get("name"), context.get("title"), module_copy["fallback"])
    detail = _first_text(
        raw.get("content"), raw.get("body"), raw.get("description"), context.get("description"), summary
    )
    quote = _first_text(raw.get("child_words"), raw.get("quote"), context.get("child_words"), context.get("quote"))
    return {
        "id": str(event.get("id") or ""),
        "module": module,
        "title": title,
        "summary": summary,
        "detail": detail,
        "quote": quote,
        "occurred_at": str(event.get("occurred_at") or ""),
        "status": module_copy["highlight"],
        "unlocked": True,
        "event_type": str(event.get("event_type") or "exploration_event"),
        "kind": "highlight",
    }


def _highlight_rank(event: dict[str, Any], module: str) -> tuple[float, float, str]:
    strong = 1.0 if event.get("evidence_level") == "strong" else 0.0
    occurred_at = str(event.get("occurred_at") or "")
    if module == "story":
        return float(_content_length(event)), strong, occurred_at
    if module == "deep_sea":
        duration = _number(event, DURATION_KEYS)
        return (1_000_000.0 - duration if duration else strong), strong, occurred_at
    if module == "career":
        score = _number(event, SCORE_KEYS)
        raw, context = _raw_context(event)
        choices = raw.get("choices") or context.get("choices") or []
        choice_count = len(choices) if isinstance(choices, list) else 0
        return score or float(choice_count), strong, occurred_at
    turns = _number(event, TURN_KEYS)
    return turns or float(_content_length(event)), strong, occurred_at


def _highlight_metric(event: dict[str, Any], module: str, usage_count: int) -> tuple[str, str]:
    if module == "story":
        length = _content_length(event)
        return "故事长度", f"{length} 字" if length else f"从 {usage_count} 次故事中选出"
    if module == "deep_sea":
        duration = _number(event, DURATION_KEYS)
        return "完成速度", _format_duration(duration) if duration else f"从 {usage_count} 次重建中选出"
    if module == "career":
        score = _number(event, SCORE_KEYS)
        raw, context = _raw_context(event)
        choices = raw.get("choices") or context.get("choices") or []
        if score:
            return "体验记录", f"{int(score)} 颗体验星"
        if isinstance(choices, list) and choices:
            return "体验记录", f"完成 {len(choices)} 个关键选择"
        return "体验记录", f"从 {usage_count} 次体验中选出"
    turns = _number(event, TURN_KEYS)
    return "表达记录", f"{int(turns)} 轮对话" if turns else f"从 {usage_count} 次对话中选出"


def _build_highlight(events: list[dict[str, Any]], module: str) -> dict[str, Any]:
    best = max(events, key=lambda event: _highlight_rank(event, module))
    item = _event_item(best)
    metric_label, metric_value = _highlight_metric(best, module, len(events))
    item.update({"metric_label": metric_label, "metric_value": metric_value, "usage_count": len(events)})
    return item


def _registration_item(account: dict[str, Any]) -> dict[str, Any]:
    display_name = _first_text(account.get("display_name"), "小小探索家")
    occurred_at = str(account.get("created_at") or "")
    return {
        "id": f"registration-{account.get('id', '')}",
        "module": "registration",
        "title": f"{display_name}来到探索星球",
        "summary": "这是你的第一颗星，也是所有探索故事的起点。",
        "detail": "从注册这一天开始，四座大陆会把每次使用的小脚印慢慢送到这里。",
        "quote": "从今天起，出发去发现自己的闪光点。",
        "occurred_at": occurred_at,
        "status": "星光起点",
        "unlocked": True,
        "event_type": "account_registered",
        "kind": "registration",
        "metric_label": "加入时间",
        "metric_value": "第一次出发",
        "usage_count": 0,
        "first_used_at": occurred_at,
        "last_used_at": occurred_at,
    }


def _module_summary(module: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    copy = MODULE_COPY[module]
    if not events:
        return {
            "id": f"summary-{module}",
            "module": module,
            "title": f"{copy['island']}还在等你",
            "summary": "完成第一次探索后，这里会出现你的使用时间和累计次数。",
            "detail": "现在还没有这个模块的真实使用记录。去探索一次，就能点亮这一站。",
            "quote": "每一次开始，都算一个了不起的小脚印。",
            "occurred_at": "",
            "status": "还没出发",
            "unlocked": False,
            "event_type": "module_summary",
            "kind": "module_summary",
            "metric_label": "累计使用",
            "metric_value": "0 次探索",
            "usage_count": 0,
            "first_used_at": "",
            "last_used_at": "",
        }
    ordered = sorted(events, key=lambda event: str(event.get("occurred_at") or ""))
    first, last = ordered[0], ordered[-1]
    duration = sum(_number(event, DURATION_KEYS) for event in events)
    metric_value = f"{len(events)} 次探索"
    if duration:
        metric_value += f" · 累计 {_format_duration(duration)}"
    latest = _event_item(last)
    return {
        **latest,
        "id": f"summary-{module}",
        "title": f"{copy['island']}的使用小结",
        "summary": f"从第一次使用到最近一次，共留下 {len(events)} 个真实脚印。",
        "detail": f"你已经在{copy['island']}使用了 {len(events)} 次。最近一次记录是：{latest['summary']}",
        "status": "模块已点亮",
        "event_type": "module_summary",
        "kind": "module_summary",
        "metric_label": "累计使用",
        "metric_value": metric_value,
        "usage_count": len(events),
        "first_used_at": str(first.get("occurred_at") or ""),
        "last_used_at": str(last.get("occurred_at") or ""),
    }


def build_explorer_collection(account: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    """作品只返回模块高光；足迹返回注册起点与四个模块的使用小结。"""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        module = event.get("module") if event.get("module") in MODULE_COPY else "chat"
        grouped[module].append(event)

    highlights = [_build_highlight(grouped[module], module) for module in MODULE_ORDER if grouped[module]]
    milestones = [_registration_item(account)]
    milestones.extend(_module_summary(module, grouped[module]) for module in MODULE_ORDER)
    return {
        "account": account,
        "works": highlights,
        "milestones": milestones,
        "source": "evidence_highlights_and_usage_summary",
    }
