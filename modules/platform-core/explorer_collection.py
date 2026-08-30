"""把统一证据整理成“全部完成作品 + 模块高光 + 账号完成历程”。"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


MODULE_COPY = {
    "story": {"island": "想象之洲", "fallback": "想象之洲的新故事", "highlight": "完整创作高光"},
    "deep_sea": {"island": "创造之洲", "fallback": "创造之洲的新设计", "highlight": "完整重建高光"},
    "career": {"island": "未来之洲", "fallback": "未来之洲的新体验", "highlight": "完整体验高光"},
    "chat": {"island": "倾听之洲", "fallback": "倾听之洲的新发现", "highlight": "充分表达高光"},
}
MODULE_ORDER = tuple(MODULE_COPY)
DURATION_KEYS = ("duration_seconds", "elapsed_seconds", "duration", "elapsed", "time_spent_seconds")
CAREER_NAMES = {
    "doctor": "社区医生",
    "firefighter": "消防员",
    "teacher": "小学教师",
    "chef": "厨师",
    "journalist": "记者",
    "animal_caretaker": "动物保护员",
}
DEEP_SEA_LEVEL_NAMES = {1: "珊瑚公寓", 2: "洋流电网", 3: "海洋议事厅"}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_text(*values: Any) -> str:
    return next((text for value in values if (text := _text(value))), "")


def _raw_context(event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = event.get("raw_evidence") if isinstance(event.get("raw_evidence"), dict) else {}
    context = event.get("context") if isinstance(event.get("context"), dict) else {}
    return raw, context


def _source_number(source: dict[str, Any], keys: tuple[str, ...]) -> float:
    for key in keys:
        value = source.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
            return float(value)
    return 0.0


def _number(event: dict[str, Any], keys: tuple[str, ...]) -> float:
    raw, context = _raw_context(event)
    for source in (raw, context, event):
        value = _source_number(source, keys)
        if value:
            return value
        if any(source.get(key) == 0 for key in keys):
            return 0.0
    return 0.0


def _has_number(event: dict[str, Any], keys: tuple[str, ...]) -> bool:
    raw, context = _raw_context(event)
    return any(
        isinstance(source.get(key), (int, float)) and not isinstance(source.get(key), bool)
        for source in (raw, context, event)
        for key in keys
    )


def _timestamp(value: Any) -> float:
    text = _text(value)
    if not text:
        return 0.0
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except ValueError:
        return 0.0


def _format_total_duration(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    if total < 60:
        return "不到1分钟"
    minutes = total // 60
    hours, remainder = divmod(minutes, 60)
    if hours and remainder:
        return f"{hours}小时{remainder}分"
    if hours:
        return f"{hours}小时"
    return f"{minutes}分钟"


def _activity_key(event: dict[str, Any], module: str) -> tuple[str, bool]:
    raw, context = _raw_context(event)
    explicit = _first_text(
        context.get("activity_id"),
        raw.get("activity_id"),
        context.get("session_id"),
        context.get("workday_run_id"),
    )
    if explicit:
        return explicit, True
    if module == "story" and context.get("story_id") is not None:
        return f"story-{context['story_id']}", True
    return f"legacy-{event.get('id') or id(event)}", False


def _level(event: dict[str, Any]) -> int:
    raw, context = _raw_context(event)
    value = context.get("level", raw.get("level"))
    if isinstance(value, str):
        value = value.replace("LEVEL_", "")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed in DEEP_SEA_LEVEL_NAMES else 0


def _build_activity(module: str, key: str, events: list[dict[str, Any]], explicit_key: bool) -> dict[str, Any]:
    ordered = sorted(events, key=lambda item: _timestamp(item.get("occurred_at")))
    raw_items = [_raw_context(event)[0] for event in ordered]
    levels = sorted({level for event in ordered if (level := _level(event))})
    summary_events = [event for event in ordered if event.get("event_type") == "deep_sea_session_completed"]
    if module == "deep_sea" and summary_events:
        reported_levels = int(_number(summary_events[-1], ("completed_levels",)))
        if reported_levels > len(levels):
            levels = list(range(1, min(reported_levels, 3) + 1))

    completed = any(raw.get("completed") is True for raw in raw_items)
    if module == "deep_sea":
        # 深海每一关本身都是一件可回看的重建成果；同一 activity_id 下的多关
        # 仍只算一次探索，三关全完再升级为“完整重建”高光。
        completed = bool(summary_events) or (bool(levels) and completed) or not explicit_key
    elif not completed:
        # 旧事件均来自完成点，保留兼容性；新事件可显式传 completed:false 排除。
        completed = not any(raw.get("completed") is False for raw in raw_items)

    duration_events = [event for event in ordered if _has_number(event, DURATION_KEYS)]
    if module == "deep_sea" and summary_events and _has_number(summary_events[-1], DURATION_KEYS):
        duration = _number(summary_events[-1], DURATION_KEYS)
        duration_known = True
    else:
        duration = sum(_number(event, DURATION_KEYS) for event in duration_events)
        duration_known = bool(duration_events)

    latest = ordered[-1]
    return {
        "id": key,
        "module": module,
        "events": ordered,
        "latest": latest,
        "completed": completed,
        "occurred_at": str(latest.get("occurred_at") or ""),
        "first_at": str(ordered[0].get("occurred_at") or ""),
        "duration_seconds": duration,
        "duration_known": duration_known,
        "levels": levels,
        "strong_count": sum(event.get("evidence_level") == "strong" for event in ordered),
    }


def _activities_for_module(module: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    explicit_by_key: dict[str, bool] = {}
    for event in events:
        key, explicit = _activity_key(event, module)
        grouped[key].append(event)
        explicit_by_key[key] = explicit_by_key.get(key, False) or explicit
    return [
        _build_activity(module, key, grouped[key], explicit_by_key[key])
        for key in grouped
    ]


def _activity_number(activity: dict[str, Any], keys: tuple[str, ...]) -> float:
    values = [_number(event, keys) for event in activity["events"]]
    if not values:
        return 0.0
    return max(values)


def _activity_field_sum(activity: dict[str, Any], *keys: str) -> float:
    return sum(_number(event, (key,)) for event in activity["events"] for key in keys)


def _activity_content_length(activity: dict[str, Any]) -> int:
    explicit = int(_activity_number(activity, ("word_count", "character_count", "content_length")))
    if explicit:
        return explicit
    lengths = []
    for event in activity["events"]:
        raw, context = _raw_context(event)
        content = _first_text(raw.get("content"), raw.get("story"), raw.get("body"), raw.get("text"), context.get("content"))
        lengths.append(len(content))
    return max(lengths, default=0)


def _deep_adjustments(activity: dict[str, Any]) -> float:
    summaries = [
        event for event in activity["events"]
        if event.get("event_type") == "deep_sea_session_completed"
    ]
    if summaries and _has_number(summaries[-1], ("meaningful_adjustments",)):
        return _number(summaries[-1], ("meaningful_adjustments",))
    return _activity_field_sum(activity, "meaningful_adjustments", "rotate_count")


def _activity_title(activity: dict[str, Any]) -> str:
    module = activity["module"]
    latest = activity["latest"]
    raw, context = _raw_context(latest)
    if module == "deep_sea" and activity["levels"] == [1, 2, 3]:
        return "深海基地完整重建"
    title = _first_text(raw.get("title"), raw.get("name"), context.get("title"))
    if title:
        return title[:60]
    if module == "deep_sea":
        if activity["levels"]:
            return f"{DEEP_SEA_LEVEL_NAMES[activity['levels'][-1]]}重建"
    if module == "career":
        career_id = _first_text(raw.get("career_id"), context.get("career_id"))
        career_name = _first_text(raw.get("career_name"), context.get("career_name"), CAREER_NAMES.get(career_id))
        if career_name:
            return f"{career_name}的一天"
    if module == "chat":
        topic = _first_text(raw.get("topic"), raw.get("topic_title"), context.get("topic"))
        if topic:
            return f"聊聊{topic}"
    return MODULE_COPY[module]["fallback"]


def _activity_item(activity: dict[str, Any]) -> dict[str, Any]:
    module = activity["module"]
    module_copy = MODULE_COPY[module]
    latest = activity["latest"]
    raw, context = _raw_context(latest)
    summaries = [
        _text(event.get("behavior_summary"))
        for event in activity["events"]
        if _text(event.get("behavior_summary"))
    ]
    summary = summaries[-1] if summaries else "这里收着一次认真尝试。"
    detail = _first_text(
        raw.get("work_content"), raw.get("content"), raw.get("story"), raw.get("body"),
        raw.get("description"), context.get("description"), summary,
    )
    quote = _first_text(raw.get("child_words"), raw.get("quote"), context.get("child_words"), context.get("quote"))
    return {
        "id": f"activity-{module}-{activity['id']}",
        "module": module,
        "title": _activity_title(activity),
        "summary": summary,
        "detail": detail,
        "quote": quote[:120],
        "occurred_at": activity["occurred_at"],
        "status": "阶段作品已收藏" if module == "deep_sea" and activity["levels"] != [1, 2, 3] else "完成作品已收藏",
        "unlocked": True,
        "event_type": str(latest.get("event_type") or "exploration_event"),
        "kind": "work",
        "is_highlight": False,
        "snapshot_url": _first_text(context.get("snapshot_url"), raw.get("snapshot_url")),
    }


def _highlight_rank(activity: dict[str, Any]) -> tuple[float, ...]:
    module = activity["module"]
    recent = _timestamp(activity["occurred_at"])
    strong = float(activity["strong_count"])
    if module == "chat":
        return (
            _activity_number(activity, ("total_child_chars", "character_count")),
            _activity_number(activity, ("long_turn_count",)),
            _activity_number(activity, ("turn_count", "turns", "message_count")),
            strong,
            recent,
        )
    if module == "story":
        completion_mode = any(
            _raw_context(event)[0].get("completion_mode") == "child" for event in activity["events"]
        )
        return (
            _activity_number(activity, ("turn_number", "turn_count")),
            _activity_number(activity, ("ending_length", "character_count", "content_length")),
            float(_activity_content_length(activity)),
            float(completion_mode),
            strong,
            recent,
        )
    if module == "deep_sea":
        adjustments = _deep_adjustments(activity)
        return float(len(activity["levels"])), adjustments, strong, recent
    completed = _activity_number(activity, ("completed_stages",))
    total = _activity_number(activity, ("stage_count",))
    completion_ratio = completed / total if total else 0.0
    interactions = _activity_number(activity, ("interaction_count",))
    adjustments = _activity_field_sum(activity, "adjustment_count", "retry_count")
    return completion_ratio, interactions, adjustments, strong, recent


def _highlight_metric(activity: dict[str, Any]) -> tuple[str, str]:
    module = activity["module"]
    if module == "chat":
        turns = int(_activity_number(activity, ("turn_count", "turns", "message_count")))
        long_turns = int(_activity_number(activity, ("long_turn_count",)))
        value = f"{turns} 轮对话"
        if long_turns:
            value += f" · {long_turns} 次长表达"
        return "表达记录", value
    if module == "story":
        turns = int(_activity_number(activity, ("turn_number", "turn_count")))
        ending = int(_activity_number(activity, ("ending_length",)))
        content_length = _activity_content_length(activity)
        value = f"{turns} 轮共创" if turns else (f"{content_length} 字作品" if content_length else "完成一篇故事")
        if ending:
            value += f" · 结尾 {ending} 字"
        return "创作记录", value
    if module == "deep_sea":
        levels = len(activity["levels"])
        adjustments = int(_deep_adjustments(activity))
        value = f"完成 {levels or 1} 个任务"
        if adjustments:
            value += f" · 调整 {adjustments} 次"
        return "重建记录", value
    completed = int(_activity_number(activity, ("completed_stages",)))
    total = int(_activity_number(activity, ("stage_count",)))
    interactions = int(_activity_number(activity, ("interaction_count",)))
    value = f"完成 {completed}/{total} 个阶段" if total else "完成一次职业体验"
    if interactions:
        value += f" · 主动尝试 {interactions} 次"
    return "体验记录", value


def _highlight_reason(activity: dict[str, Any]) -> str:
    module = activity["module"]
    if module == "chat":
        chars = int(_activity_number(activity, ("total_child_chars", "character_count")))
        if chars:
            return f"这次围绕一个话题表达得最充分，共说出了 {chars} 个字。"
        return _activity_item(activity)["summary"]
    if module == "story":
        turns = int(_activity_number(activity, ("turn_number", "turn_count")))
        ending = int(_activity_number(activity, ("ending_length",)))
        if ending:
            return f"这篇故事连续参与了 {turns} 轮，还自己写下了 {ending} 字的结尾。"
        return f"这篇故事连续参与了 {turns} 轮，把故事完整创作到了结局。"
    if module == "deep_sea":
        adjustments = int(_deep_adjustments(activity))
        task_count = len(activity["levels"]) or 1
        if task_count == 3:
            return f"这次完成了三处基地任务，并根据结果调整了 {adjustments} 次。" if adjustments else "这次完整完成了三处基地任务，留下了一次完整重建记录。"
        return f"这次完成了 {task_count} 处基地任务，并根据结果调整了 {adjustments} 次。" if adjustments else f"这次完成了 {task_count} 处基地任务，留下了一次阶段重建记录。"
    completed = int(_activity_number(activity, ("completed_stages",)))
    interactions = int(_activity_number(activity, ("interaction_count",)))
    return f"这次完成了全部 {completed} 个职业阶段，还主动尝试了 {interactions} 次。"


def _build_highlight(activities: list[dict[str, Any]]) -> dict[str, Any]:
    best = max(activities, key=_highlight_rank)
    item = _activity_item(best)
    metric_label, metric_value = _highlight_metric(best)
    item.update({
        "summary": _highlight_reason(best),
        "metric_label": metric_label,
        "metric_value": metric_value,
        "usage_count": len(activities),
        "kind": "highlight",
        "is_highlight": True,
        "status": (
            "阶段重建高光"
            if best["module"] == "deep_sea" and best["levels"] != [1, 2, 3]
            else MODULE_COPY[best["module"]]["highlight"]
        ),
    })
    return item


def _build_work(activity: dict[str, Any]) -> dict[str, Any]:
    item = _activity_item(activity)
    metric_label, metric_value = _highlight_metric(activity)
    item.update({
        "metric_label": metric_label,
        "metric_value": metric_value,
        "usage_count": 1,
    })
    return item


def _registration_item(account: dict[str, Any]) -> dict[str, Any]:
    display_name = _first_text(account.get("display_name"), "小小探索家")
    occurred_at = str(account.get("created_at") or "")
    return {
        "id": f"registration-{account.get('id', '')}",
        "module": "registration",
        "title": f"{display_name}来到探索星球",
        "summary": "这是你的第一颗星，也是所有探索故事的起点。",
        "detail": "从注册这一天开始，四座大陆会把每次完成的小脚印慢慢送到这里。",
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
        "duration_seconds": 0,
        "duration_coverage": 0.0,
    }


def _module_summary(module: str, activities: list[dict[str, Any]]) -> dict[str, Any]:
    copy = MODULE_COPY[module]
    if not activities:
        return {
            "id": f"summary-{module}",
            "module": module,
            "title": f"{copy['island']}还在等你",
            "summary": "完成第一次探索后，这里会出现你的完成时间和累计次数。",
            "detail": "现在还没有这个模块的真实完成记录。去探索一次，就能点亮这一站。",
            "quote": "每一次开始，都算一个了不起的小脚印。",
            "occurred_at": "",
            "status": "还没出发",
            "unlocked": False,
            "event_type": "module_summary",
            "kind": "module_summary",
            "metric_label": "累计完成",
            "metric_value": "0 次探索",
            "usage_count": 0,
            "first_used_at": "",
            "last_used_at": "",
            "duration_seconds": 0,
            "duration_coverage": 0.0,
        }

    ordered = sorted(activities, key=lambda activity: _timestamp(activity["occurred_at"]))
    first, last = ordered[0], ordered[-1]
    duration_activities = [activity for activity in ordered if activity["duration_known"]]
    duration = sum(activity["duration_seconds"] for activity in duration_activities)
    coverage = len(duration_activities) / len(ordered)
    metric_value = f"{len(ordered)} 次探索"
    if duration:
        prefix = "累计" if coverage == 1 else "已记录时长"
        metric_value += f" · {prefix} {_format_total_duration(duration)}"
    latest = _activity_item(last)
    return {
        **latest,
        "id": f"summary-{module}",
        "title": f"{copy['island']}的完成小结",
        "summary": f"从第一次完成到最近一次，共留下 {len(ordered)} 个真实脚印。",
        "detail": f"已经在{copy['island']}完成了 {len(ordered)} 次探索。最近一次记录是：{latest['detail']}",
        "status": "模块已点亮",
        "event_type": "module_summary",
        "kind": "module_summary",
        "metric_label": "累计完成",
        "metric_value": metric_value,
        "usage_count": len(ordered),
        "first_used_at": first["first_at"],
        "last_used_at": last["occurred_at"],
        "duration_seconds": int(round(duration)),
        "duration_coverage": coverage,
    }


def build_explorer_collection(account: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    """作品返回每次完成成果并标出模块高光；足迹返回完成小结。"""
    grouped_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        module = event.get("module")
        if module in MODULE_COPY:
            grouped_events[module].append(event)

    grouped_activities = {
        module: [
            activity
            for activity in _activities_for_module(module, grouped_events[module])
            if activity["completed"]
        ]
        for module in MODULE_ORDER
    }
    works: list[dict[str, Any]] = []
    highlights: list[dict[str, Any]] = []
    for module in MODULE_ORDER:
        activities = grouped_activities[module]
        if not activities:
            continue
        best = max(activities, key=_highlight_rank)
        highlight = _build_highlight(activities)
        highlights.append(highlight)
        works.append(highlight)
        works.extend(
            _build_work(activity)
            for activity in sorted(activities, key=lambda item: _timestamp(item["occurred_at"]), reverse=True)
            if activity is not best
        )
    milestones = [_registration_item(account)]
    milestones.extend(_module_summary(module, grouped_activities[module]) for module in MODULE_ORDER)
    return {
        "account": account,
        "works": works,
        "highlights": highlights,
        "milestones": milestones,
        "source": "activity_highlights_and_completion_summary",
    }
