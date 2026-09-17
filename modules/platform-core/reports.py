"""Core 内置的可解释报告规则；不把行为记录转换为能力分数或排名。"""

from __future__ import annotations

import re
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
ANALYSIS_VERSION = "dimension-observation-v7"
CAREER_NAMES = {"doctor":"社区医生","firefighter":"消防员","teacher":"小学教师","chef":"餐厅厨师","journalist":"报社记者","animal_caretaker":"动物保护员"}
CAREER_STAGE_TITLES = {
    "doctor":["开诊台准备","病人分诊","问诊检查"], "firefighter":["装备柜点检","接警出动","现场救援路径规划"],
    "teacher":["布置晨间教室","课堂管理","和朵朵聊一聊"], "chef":["后厨开档","午餐炒饭流程","出餐高峰应对"],
    "journalist":["编辑部线索墙","组织报道线索","采访调查"], "animal_caretaker":["晨间巡护打卡","动物救助优先级","动物健康检查"],
}
CHAT_ACTIVITY_NAMES = {"picture_choice": "图片选择", "sequence_order": "顺序整理", "sentence_completion": "补句创作"}


def _chat_activity_details(raw: dict[str, Any]) -> list[str]:
    activities = raw.get("interactionActivities", []) if isinstance(raw.get("interactionActivities"), list) else []
    details = []
    for activity in activities:
        if not isinstance(activity, dict):
            continue
        name = CHAT_ACTIVITY_NAMES.get(str(activity.get("activityType", "")), "互动小任务")
        response = str(activity.get("response", "")).strip()
        revisions = max(0, int(activity.get("revisionCount", 0) or 0))
        text = f"{name}：孩子留下{_quote_child(response[:140])}" if response else f"{name}：孩子完成了这项互动"
        if revisions:
            text += f"，过程中修改了 {revisions} 次"
        details.append(text + "。")
    return details


def _chat_activity_source(raw: dict[str, Any]) -> str:
    names = list(dict.fromkeys(detail.split("：", 1)[0] for detail in _chat_activity_details(raw)))
    return "、".join(names)


def _key(value: str) -> str | None:
    value = SYNONYMS.get(value, value)
    return value if value in DIMENSIONS else None


# —— 与报告智能体保持一致的证据清洗规则 ——————————————————————————
# 语音识别会把中文逐词切开，入口提示语也会被回填成“孩子的原话”。
# 这些内容必须先清洗再判断，否则会以重复的泛化文案出现在家长报告里。
_CJK_SPACE = re.compile(r"(?<=[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef])\s+(?=[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef])")
_PUNCT_SPACE = re.compile(r"\s*([，。！？；：、,.!?;:])\s*")
_ECHO_EXACT = {
    "今天最想记住的事", "今天最想记住的事。", "我的新发现", "兴趣爱好", "朋友相处",
    "今天最开心的事", "今天最难过的事", "最近发生的事", "说说你的发现",
}
_ECHO_PREFIX = re.compile(r"^(今天最想|今天最|最近最想|最近最|说说你|你最喜欢|你最近|如果让你|请你说)")
_FILLER = re.compile(
    r"我|你|他|她|它|的|了|是|在|和|都|很|就|也|不|这|那|一|个|有|会|要|可以|什么|怎么|"
    r"今天|最近|一起|我们|他们|自己|时候|事情|东西|然后|还有|就是|其实|真的|喜欢|觉得"
)
# 每个维度只说明一次边界，避免同一句话在分析里重复出现。
DIMENSION_ANGLE = {
    "linguistic": "语言维度只看孩子怎样组织词语、因果和讲述顺序。",
    "logical": "逻辑维度只看孩子怎样比较条件、检查结果和调整做法。",
    "spatial": "空间维度只看孩子怎样处理位置、方向和连接关系。",
    "interpersonal": "人际维度只看孩子怎样理解、回应他人以及处理分歧。",
    "intrapersonal": "内省维度只看孩子怎样说出自己的感受、偏好和调整办法。",
    "naturalistic": "自然观察维度只看孩子依据哪些特征完成分类和判断。",
}


def _clean_words(value: Any) -> str:
    text = re.sub(r"\s*\n+\s*", "", str(value or "")).replace("\u3000", " ").strip()
    if not text:
        return ""
    previous = None
    while previous != text:
        previous = text
        text = _CJK_SPACE.sub("", text)
    text = _PUNCT_SPACE.sub(r"\1", text).strip()
    return re.sub(r"^[的了地得是就在和]\s*[，,、]?\s*", "", text).strip()


def _is_meaningful(value: Any, topic: str = "") -> bool:
    cleaned = _clean_words(value)
    if not cleaned or cleaned in _ECHO_EXACT or _ECHO_PREFIX.match(cleaned):
        return False
    topic_cleaned = _clean_words(topic)
    if topic_cleaned and cleaned == topic_cleaned:
        return False
    if len(cleaned) < 6:
        return False
    return len(_FILLER.sub("", cleaned)) >= 3


def _clip(value: Any, limit: int) -> str:
    """按句读截断，避免出现半句话或未闭合的引号。"""
    text = re.sub(r"\s*\n+\s*", "", str(value or "")).strip()
    if len(text) <= limit:
        return text
    window = text[:limit]
    for pattern in (r"[。！？!?]", r"[；;]", r"[，,]"):
        found = list(re.finditer(pattern, window))
        if found and found[-1].end() >= max(10, limit // 3):
            window = window[: found[-1].end()]
            break
    else:
        window = window.rstrip("，。；：、,.!?;:") + "…"
    if window.count("“") > window.count("”"):
        opening = window.rfind("“")
        window = (window[:opening].rstrip("，。；：、") + "…") if opening >= 10 else window.replace("“", "")
    return window


def _clip_phrase(value: Any, limit: int) -> str:
    return _clip(value, limit).rstrip("，、；：。").strip()


def _quote_child(value: Any) -> str:
    """把孩子原话包成引语；原话自带引号时外层改用「」，避免嵌套读不通。"""
    text = str(value or "").strip()
    if not text:
        return ""
    return f"「{text}」" if re.search(r"[“”\"]", text) else f"“{text}”"


def _dedupe_sentences(candidates: list[str], limit: int = 3) -> list[str]:
    kept: list[str] = []
    fingerprints: list[str] = []
    for text in candidates:
        value = text.strip().rstrip("。；;")
        if not value:
            continue
        fingerprint = re.sub(r"[\s，。；：、,.!?;:“”\"'‘’（）()]+", "", value)
        if not fingerprint:
            continue
        if any(fingerprint[:24] == other[:24] or fingerprint in other or other in fingerprint or (len(fingerprint) >= 16 and fingerprint[-16:] == other[-16:]) for other in fingerprints):
            continue
        fingerprints.append(fingerprint)
        kept.append(value)
        if len(kept) == limit:
            break
    return kept


def _cumulative_child_story(items: list[dict[str, Any]]) -> str:
    if not items:
        return "还没有可回看的探索记录。完成一次相关探索后，我会把你的真实表现写在这里。"
    if len(items) == 1:
        item = items[0]
        raw = item.get("raw_evidence", {}) if isinstance(item.get("raw_evidence"), dict) else {}
        context = item.get("context", {}) if isinstance(item.get("context"), dict) else {}
        summary = context.get("sessionSummary", {}) if isinstance(context.get("sessionSummary"), dict) else {}
        module = str(item.get("module"))
        if module == "story":
            title = str(summary.get("storyTitle", "")).strip() or str(raw.get("storyTitle", "")).strip() or "这次故事"
            outline = str(summary.get("storySynopsis", "") or summary.get("storyOutline", "")).strip()
            highlight = str(summary.get("childHighlight", "")).strip()
            highlight_text = f" 精彩的一句是：{_quote_child(highlight[:70])}。" if highlight else ""
            return f"你和伙伴共创了《{title}》。故事梗概：{outline[:120].rstrip('。')}。{highlight_text}" if outline else f"你完成了《{title}》的共创，并写下了 {raw.get('contributionCount', 0)} 个故事片段。"
        if module == "chat":
            turns = raw.get("childTurns", []) if isinstance(raw.get("childTurns"), list) else []
            excerpts = [_clean_words(turn.get("text", "")) for turn in turns if isinstance(turn, dict) and _clean_words(turn.get("text", ""))]
            topic = str(raw.get("topicKey", "")).strip()
            words = _clean_words(summary.get("childWords", ""))
            if words:
                people = [name for name in ("同学", "朋友", "老师", "爸爸", "妈妈", "家人", "伙伴") if name in words]
                relation = f"你还说清了自己对{'、'.join(people)}的关注和期待。" if people else "你把自己的感受和在意的事情说得很清楚。"
                activity = _chat_activity_source(raw)
                source = f" 你还通过{activity}留下了更具体的想法。" if activity else ""
                return f"这次聊天中，你说：{_quote_child(words[:90])}。{relation}{source}"
            if excerpts:
                words = excerpts[-1]
                people = [name for name in ("同学", "朋友", "老师", "爸爸", "妈妈", "家人", "伙伴") if name in words]
                relation = f"你还说清了自己对{'、'.join(people)}的关注和期待。" if people else "你把自己的感受和在意的事情说得很清楚。"
                activity = _chat_activity_source(raw)
                source = f" 你还通过{activity}留下了更具体的想法。" if activity else ""
                return f"这次聊天中，你说：{_quote_child(words[:90])}。{relation}{source}"
            return f"这次聊天里，你围绕“{topic}”留下了自己的想法。"
        if module == "deep_sea":
            level = int(raw.get("level", 0) or 0)
            if level == 1:
                review = summary.get("levelOneReview", {}) if isinstance(summary.get("levelOneReview"), dict) else {}
                pairs = [str(value).strip() for value in review.get("matchedRelationships", []) if str(value).strip()] if isinstance(review.get("matchedRelationships"), list) else []
                return f"在第一关“珊瑚公寓”里，你根据栖息地和共生关系，为{'、'.join(pairs)}找到了合适的位置。" if pairs else "在第一关“珊瑚公寓”里，你观察生物的栖息地和共生关系，为它们安排了合适的住处。"
            if level == 2:
                return f"在第二关“洋流电网”里，你摆放并旋转管件，检查方向，经过 {raw.get('adjustmentCount', 0)} 次调整尝试接通线路。"
            if level == 3:
                review = summary.get("levelThreeReview", {}) if isinstance(summary.get("levelThreeReview"), dict) else {}
                solution = str(review.get("solutionSummary", "")).strip()
                return f"在第三关“海洋议事厅”里，你听取双方需要并提出协调办法：{solution[:120].rstrip('。')}。" if solution else "在第三关“海洋议事厅”里，你听取不同角色的需要并尝试协调分歧。"
        if str(item.get("module")) == "career":
            task_key = str(raw.get("taskKey", ""))
            career_name = str(summary.get("careerName", "")).strip() or CAREER_NAMES.get(task_key, "这次职业")
            stages = summary.get("stageTitles", []) if isinstance(summary.get("stageTitles"), list) else []
            stages = [str(stage).strip() for stage in stages if str(stage).strip()] or CAREER_STAGE_TITLES.get(task_key, [])
            return f"在“{career_name}”体验里，你完成了{'、'.join(stages)}，走完了这个职业一天里的几项真实任务。" if stages else f"你完成了一次“{career_name}”职业体验。"
        return f"你在{MODULE_NAMES.get(str(item.get('module')), '探索活动')}里留下了一次真实的小发现：{str(item.get('behavior_summary', '')).rstrip('。')}。"
    module = str(items[0].get("module", ""))
    raw_items = [item.get("raw_evidence", {}) if isinstance(item.get("raw_evidence"), dict) else {} for item in items]
    if any(str(item.get("module")) == "deep_sea" for item in items) and all(str(item.get("module")) == "chat" or (str(item.get("module")) == "deep_sea" and int((item.get("raw_evidence") or {}).get("level", 0) or 0) == 3) for item in items):
        chats = sum(str(item.get("module")) == "chat" for item in items)
        negotiations = len(items) - chats
        return f"你留下了 {chats} 次聊天交流和 {negotiations} 次议事厅协商记录。你在交流中表达自己的感受，也在角色分歧中尝试理解双方需要并提出协调办法。"
    if module == "story":
        contributions = sum(max(0, int(raw.get("contributionCount", 0) or 0)) for raw in raw_items)
        outlines = [str(item.get("context", {}).get("sessionSummary", {}).get("storySynopsis", "") or item.get("context", {}).get("sessionSummary", {}).get("storyOutline", "")).strip() for item in items if isinstance(item.get("context"), dict) and isinstance(item.get("context", {}).get("sessionSummary"), dict)]
        outlines = [text for text in outlines if text]
        review = f"最近的故事讲到：{'；'.join(_clip(text, 70) for text in outlines[-2:])}" if outlines else ""
        highlights = [str(item.get("context", {}).get("sessionSummary", {}).get("childHighlight", "")).strip() for item in items if isinstance(item.get("context"), dict) and isinstance(item.get("context", {}).get("sessionSummary"), dict)]
        highlights = [text for text in highlights if text]
        highlight_text = f"精彩的一句是：{_quote_child(_clip_phrase(highlights[-1], 70))}。" if highlights else ""
        return f"你已经完成了 {len(items)} 次故事共创，共贡献了 {contributions} 个故事片段。{review}{highlight_text}"
    if module == "chat":
        turns = sum(max(0, int(raw.get("turnCount", 0) or 0)) for raw in raw_items)
        topics = list(dict.fromkeys(str(raw.get("topicKey", "")).strip() for raw in raw_items if str(raw.get("topicKey", "")).strip()))
        topic_text = f"你聊过“{'”“'.join(topics[-3:])}”。" if topics else ""
        excerpts = [_clean_words(turn.get("text", "")) for raw in raw_items for turn in raw.get("childTurns", []) if isinstance(turn, dict) and _clean_words(turn.get("text", ""))]
        excerpt_text = f"你分享过：{_quote_child('；'.join(_clip_phrase(text, 45) for text in excerpts[-2:]))}。" if excerpts else ""
        people = [name for name in ("同学", "朋友", "老师", "爸爸", "妈妈", "家人", "伙伴") if any(name in text for text in excerpts)]
        relation_text = f"你还谈到了自己对{'、'.join(people)}的关注和期待。" if people else ""
        activities = list(dict.fromkeys(name for raw in raw_items for name in _chat_activity_source(raw).split("、") if name))
        activity_text = f"你还做过{'、'.join(activities)}，这些小任务里的选择和原话也一起保留了。" if activities else ""
        return f"你已经完成了 {len(items)} 次聊天。{topic_text}{excerpt_text}{relation_text}{activity_text}"
    if module == "career":
        careers = list(dict.fromkeys(CAREER_NAMES.get(str(raw.get("taskKey", "")), "这次职业") for raw in raw_items))
        return f"你已经完成了 {len(items)} 次职业体验，体验过{'、'.join(careers)}。这些职业一天中的真实任务都收藏在这颗星里。"
    return f"你已经完成了 {len(items)} 次相关探索，这颗星保留着之前的全部互动结果。"


def _dimension_event_summary(item: dict[str, Any], dimension: str) -> str:
    """返回该事件在这个维度上的可回溯事实；返回空串表示不构成证据。"""
    raw = item.get("raw_evidence", {}) if isinstance(item.get("raw_evidence"), dict) else {}
    context = item.get("context", {}) if isinstance(item.get("context"), dict) else {}
    summary = context.get("sessionSummary", {}) if isinstance(context.get("sessionSummary"), dict) else {}
    if str(item.get("module")) == "chat":
        topic = str(raw.get("topicKey", "")).strip()
        words = _clean_words(summary.get("childWords", ""))
        people = [name for name in ("同学", "朋友", "老师", "爸爸", "妈妈", "家人", "伙伴") if name in words]
        source = _chat_activity_source(raw)
        source_text = f"（来自{source}活动）" if source else ""
        if not _is_meaningful(words, topic):
            return ""
        if dimension == "interpersonal":
            return f"孩子在聊天中说：{_quote_child(_clip_phrase(words, 120))}，其中明确提到了{'、'.join(people)}{source_text}。" if people else ""
        if dimension == "intrapersonal":
            return f"孩子在聊天中说：{_quote_child(_clip_phrase(words, 120))}{source_text}。"
    if str(item.get("module")) == "career" and dimension == "intrapersonal":
        reflections = summary.get("mentorReflections", []) if isinstance(summary.get("mentorReflections"), list) else []
        answers = [_clean_words(value.get("answer", "")) for value in reflections if isinstance(value, dict) and str(value.get("answer", "")).strip()]
        if answers: return f"在职业导师追问中，孩子回答：{_quote_child(_clip_phrase(answers[-1], 140))}。"
    if str(item.get("module")) == "deep_sea":
        level = int(raw.get("level", 0) or 0)
        if level == 1 and dimension == "naturalistic":
            review = summary.get("levelOneReview", {}) if isinstance(summary.get("levelOneReview"), dict) else {}
            pairs = [str(value).strip() for value in review.get("matchedRelationships", []) if str(value).strip()] if isinstance(review.get("matchedRelationships"), list) else []
            return f"孩子依据栖息地和共生关系完成生态配对：{'、'.join(pairs)}。" if pairs else "孩子比较生物特征、栖息地和共生关系后完成生态配对。"
        if level == 1 and dimension == "logical": return "孩子先比较生物与住处的匹配条件，再检查配对结果是否正确。"
        if level == 1 and dimension == "spatial":
            successful, total = int(raw.get("successfulPairs", 0) or 0), int(raw.get("totalPairs", 0) or 0)
            result = f"，共完成 {successful}/{total} 组配对" if successful and total else ""
            return f"孩子按生物的栖息位置摆放卡片、检查每一组是否放对{result}。"
        if level == 2 and dimension == "spatial": return "孩子摆放并旋转管件来规划洋流线路。"
        if level == 2 and dimension == "logical": return "孩子检查线路断点与连通结果，再调整连接方案。"
        if str(item.get("event_type")) == "deep-sea.session-completed.v1":
            levels = int(raw.get("completedLevels", 0) or 0)
            adjustments = int(raw.get("adjustmentCount", 0) or 0)
            return f"孩子完整走完了深海基地的 {levels or 3} 个关卡（珊瑚公寓、洋流电网、海洋议事厅），过程中一共调整 {adjustments} 次。"
    if str(item.get("module")) == "story":
        raw_title = str(summary.get("storyTitle") or raw.get("storyTitle") or "这次故事").strip()
        highlight = str(summary.get("childHighlight", "")).strip()
        synopsis = str(summary.get("storySynopsis") or summary.get("storyOutline") or "").strip()
        count = max(0, int(raw.get("contributionCount", 0) or 0))
        if highlight:
            return f"在《{raw_title}》的共创中，孩子写下：{_quote_child(_clip_phrase(highlight, 100))}。"
        if synopsis:
            return f"孩子参与《{raw_title}》的情节创作，故事讲到{_clip_phrase(synopsis, 90)}。"
        if count:
            return f"孩子完成《{raw_title}》的共创，写下 {count} 个故事片段。"
    if str(item.get("module")) == "career":
        career = str(summary.get("careerName", "")).strip() or CAREER_NAMES.get(str(raw.get("taskKey", "")), "这次职业")
        stages = summary.get("stageTitles", []) if isinstance(summary.get("stageTitles"), list) else []
        stages = [str(value).strip() for value in stages if str(value).strip()] or CAREER_STAGE_TITLES.get(str(raw.get("taskKey", "")), [])
        attempts = max(0, int(raw.get("attemptCount", 0) or 0))
        hints = max(0, int(raw.get("hintCount", 0) or 0))
        extra = "、".join(part for part in [f"主动尝试 {attempts} 次" if attempts else "", f"查看提示 {hints} 次" if hints else ""] if part)
        if dimension == "intrapersonal":
            answers = [_clean_words(value.get("answer", "")) for value in (summary.get("mentorReflections", []) if isinstance(summary.get("mentorReflections"), list) else []) if isinstance(value, dict) and str(value.get("answer", "")).strip()]
            if answers:
                return f"孩子在职业导师追问中回答：{_quote_child(_clip_phrase(answers[-1], 110))}。"
        if stages:
            return f"在“{career}”体验里，孩子完成了{'、'.join(stages)}{f'，{extra}' if extra else ''}。"
        return f"孩子完成了“{career}”职业体验{f'，{extra}' if extra else ''}。"
    if str(item.get("module")) != "deep_sea" or int(raw.get("level", 0) or 0) != 3:
        return str(item.get("behavior_summary", "")).rstrip("。；")
    review = summary.get("levelThreeReview", {}) if isinstance(summary.get("levelThreeReview"), dict) else {}
    solution = str(review.get("solutionSummary", "")).strip()
    utterances = review.get("childUtterances", []) if isinstance(review.get("childUtterances"), list) else []
    utterances = [str(value).strip() for value in utterances if str(value).strip()]
    if dimension == "linguistic":
        return f"在海洋议事厅的调解中，孩子说：{_quote_child(_clip_phrase(utterances[-1], 120))}。" if utterances else ""
    return f"在海洋议事厅中，孩子听取双方需要后提出的协调方案是：{_clip(solution, 140)}。" if solution else ""


def _explain_event(item: dict[str, Any]) -> dict[str, Any]:
    """Core 降级报告也按活动内容组织，不退回同质化的数字摘要。"""
    raw = item.get("raw_evidence", {}) if isinstance(item.get("raw_evidence"), dict) else {}
    context = item.get("context", {}) if isinstance(item.get("context"), dict) else {}
    session = context.get("sessionSummary", {}) if isinstance(context.get("sessionSummary"), dict) else {}
    module, event_type = str(item.get("module", "")), str(item.get("event_type", ""))
    title, summary, details = MODULE_NAMES.get(module, "探索过程回顾"), str(item.get("behavior_summary", "")), []
    if event_type == "deep-sea.spatial-task-completed.v1":
        level = int(raw.get("level", 0) or 0)
        if level == 1:
            review = session.get("levelOneReview", {}) if isinstance(session.get("levelOneReview"), dict) else {}
            pairs = [str(value).strip() for value in review.get("matchedRelationships", []) if str(value).strip()] if isinstance(review.get("matchedRelationships"), list) else []
            title, summary = "深海基地第一关：珊瑚公寓", "孩子依据栖息地和共生关系，为海洋生物安排住处。"
            details = [f"观察与判断：孩子完成了{'、'.join(pairs)}的生态关系配对。" if pairs else "观察与判断：孩子比较生物特征、栖息地和共生关系后完成配对。", f"任务结果：成功配对 {raw.get('successfulPairs', 0)}/{raw.get('totalPairs', 4)} 组。"]
        elif level == 2:
            review = session.get("levelTwoReview", {}) if isinstance(session.get("levelTwoReview"), dict) else {}
            title, summary = "深海基地第二关：洋流电网", "孩子通过摆放、旋转和检查管件方向来规划洋流线路。"
            details = ["建造过程：孩子组合管件并检查水流方向，尝试接通起点和终点。", f"调整记录：旋转或调整了 {review.get('rotateCount', raw.get('adjustmentCount', 0))} 次。"]
        elif level == 3:
            review = session.get("levelThreeReview", {}) if isinstance(session.get("levelThreeReview"), dict) else {}
            utterances = [str(value).strip() for value in review.get("childUtterances", []) if str(value).strip()] if isinstance(review.get("childUtterances"), list) else []
            solution = str(review.get("solutionSummary", "")).strip()
            title, summary = "深海基地第三关：海洋议事厅", "孩子在角色分歧情境中完成了调解表达和方案选择。"
            details = [f"调解表达：孩子说：{_quote_child(_clip_phrase(utterances[-1], 120))}" if utterances else "调解表达：这条历史记录未保存孩子当时的逐字表达。", f"方案选择：{solution[:140]}" if solution else "方案选择：这条历史记录未保存孩子当时选择的具体方案。"]
    elif module == "story":
        story_title = str(session.get("storyTitle", "")).strip() or str(raw.get("storyTitle", "")).strip() or "故事共创"
        synopsis = str(session.get("storySynopsis", "") or session.get("storyOutline", "")).strip()
        highlight = str(session.get("childHighlight", "")).strip()
        title = f"故事共创：《{story_title}》"
        # 每段故事都写同一句总结会让家长看到一排重复卡片，这里改用本篇的真实内容。
        summary = (f"孩子参与了《{story_title}》的共创，故事讲到{_clip_phrase(synopsis, 46)}。"
                   if synopsis else f"孩子参与了《{story_title}》的共创，写下了 {max(0, int(raw.get('contributionCount', 0) or 0))} 个情节片段。")
        details = [f"故事梗概：{_clip(synopsis, 160)}" if synopsis else "故事梗概：这条历史记录没有保存可复述的完整梗概。"]
        if highlight: details.append(f"精彩表达：{_quote_child(_clip_phrase(highlight, 100))}")
    elif module == "chat":
        topic = str(raw.get("topicKey", "")).strip()
        words = _clean_words(session.get("childWords", ""))
        title = "聊天观察：真实表达"
        if _is_meaningful(words, topic):
            summary = f"这次聊天中孩子说：{_quote_child(_clip_phrase(words, 80))}。"
            details = [f"表达内容：孩子说：{_quote_child(_clip_phrase(words, 120))}"]
        else:
            summary = f"这次聊天只留下“{topic or '未记录'}”这一话题入口，没有可引用的原话。"
            details = ["表达内容：这条历史记录只留下了入口话题，没有保存可引用的原话。"]
        details.append(f"交流过程：本次共留下 {raw.get('turnCount', 0)} 轮表达。")
        details.extend(f"活动来源：{detail}" for detail in _chat_activity_details(raw))
    elif module == "career":
        task_key = str(raw.get("taskKey", "")); career = str(session.get("careerName", "")).strip() or CAREER_NAMES.get(task_key, "职业")
        stages = session.get("stageTitles", []) if isinstance(session.get("stageTitles"), list) else []
        stages = [str(value).strip() for value in stages if str(value).strip()] or CAREER_STAGE_TITLES.get(task_key, [])
        title, summary = f"职业体验：{career}", f"孩子体验了{career}一天中的真实工作环节。"
        details = [f"体验内容：完成了{'、'.join(stages)}。" if stages else "体验内容：完成了本次职业情境中的任务。", f"过程表现：主动尝试 {raw.get('attemptCount', 0)} 次，调整 {raw.get('adjustmentCount', 0)} 次。"]
        reflections = session.get("mentorReflections", []) if isinstance(session.get("mentorReflections"), list) else []
        for reflection in reflections[-2:]:
            if isinstance(reflection, dict) and str(reflection.get("answer", "")).strip(): details.insert(-1, f"导师对话：孩子回答：{_quote_child(_clip_phrase(str(reflection['answer']), 120))}")
    return {"evidence_ref": item.get("id"), "title": title, "summary": summary, "details": details or ["本次活动已留下可回溯的过程记录。"]}


def _adult_observation(key: str, items: list[dict[str, Any]]) -> str:
    if not items:
        return "暂无可观测数据。完成相关探索后，这里会结合孩子的真实行为生成观察提示。"
    latest = items[-1]
    raw = latest.get("raw_evidence", {}) if isinstance(latest.get("raw_evidence"), dict) else {}
    context = latest.get("context", {}) if isinstance(latest.get("context"), dict) else {}
    summary = context.get("sessionSummary", {}) if isinstance(context.get("sessionSummary"), dict) else {}
    title = str(summary.get("storyTitle") or raw.get("storyTitle") or summary.get("careerName") or "这次任务").strip()
    # 只有故事类记录才能写成《书名号》，否则会出现“《这次任务》”这种句子。
    story_anchor = f"《{title}》" if str(latest.get("module")) == "story" else f"“{title}”"
    observations = {
        "linguistic": [f"请孩子把{story_anchor}讲给没听过的人，观察他怎样交代人物、起因和结果", "邀请孩子为同一情节换一种开头或结尾，留意前后是否连贯", "问问孩子为什么选这句对白或这个词，记录他怎样说明表达意图", "一至两周后给出三个新关键词，请孩子再编一段并比较叙述变化"],
        "logical": ["换一个规则不同的小任务，观察孩子会先比较条件还是直接尝试", "请孩子先预测结果再验证，留意预测与检查是否对应", "结果不理想时观察孩子先检查哪一步、会怎样改变条件", "一至两周后再做相似问题，请孩子重新说出判断依据"],
        "spatial": ["换一套拼搭材料，观察孩子如何处理位置、方向和连接关系", "请孩子先画出摆放方案再搭建，对照计划与成品的变化", "旋转或挪动一个部件，观察孩子能否发现并修正连接", "一至两周后请孩子凭记忆重建布局，留意使用了哪些空间线索"],
        "interpersonal": ["谈到不同角色时，请孩子分别说说每个人想要什么", "出现分歧时请孩子先复述对方的话，再表达自己的回应", "邀请孩子提出两种兼顾双方的办法，并比较各自影响", "一至两周后在新合作中观察孩子是否会主动询问、轮流或调整分工"],
        "intrapersonal": ["任务前请孩子说说最想做和最担心的部分，留意偏好与感受表达", "卡住时让孩子选择要提示、休息还是再试，观察他如何辨认状态", "完成后请孩子选出最满意和最想修改的一步，并说明原因", "一至两周后遇到相似困难时，观察孩子是否会主动采用自己的调节办法"],
        "naturalistic": ["把活动中的分类线索换成身边物品或常见生物，观察孩子依据哪些特征归类", "请孩子解释两个对象为何放在一起，再找一个反例说明区别", "新信息与原判断不一致时，观察孩子会如何修改分类标准", "一至两周后到户外或看图鉴时，观察孩子是否主动比较特征与关系"],
    }
    return "；".join(observations[key]) + "。"


def _dedupe_events(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        marker = str(item.get("id") or f"anon-{id(item)}")
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)
    return unique


# 深海“完整通关”是三个关卡记录的合并摘要：它不单独作为证据，也不参与计数，
# 否则同一段经历会被统计两次，家长端会出现互相矛盾的数字。
DEEP_SEA_SESSION_EVENT = "deep-sea.session-completed.v1"


def _is_reportable_event(event: dict[str, Any]) -> bool:
    return str(event.get("event_type") or "") != DEEP_SEA_SESSION_EVENT


def _is_strong_record(event: dict[str, Any], completed_sessions: set[str] | None = None) -> bool:
    """判定与家长端卡片标签一致：单关记录只有整场走完才算留下完整过程。

    调用方漏填 session_completed 时，只要事件带着 session_id，仍可从同一场
    会话的“完整通关”记录里推导出来，避免数字与页面卡片对不上。
    """
    if str(event.get("evidence_level") or "") == "strong" or bool(event.get("session_completed")):
        return True
    session_id = str(event.get("session_id") or "")
    return bool(completed_sessions) and bool(session_id) and session_id in completed_sessions


def _completed_deep_sea_sessions(events: list[dict[str, Any]]) -> set[str]:
    """收集已经走完整场的深海会话 id，供单关记录回填“较完整”。"""
    return {
        str(event.get("session_id"))
        for event in events
        if str(event.get("event_type") or "") == DEEP_SEA_SESSION_EVENT and event.get("session_id")
    }


def _cross_insights(events: list[dict[str, Any]], child_name: str) -> list[dict[str, Any]]:
    """从真实记录里提炼可复核的结论，而不是一句通用说明。"""
    insights: list[dict[str, Any]] = []
    fallback_refs = [str(event["id"]) for event in events if event.get("id")][:3]

    def add(text: str, refs: list[str]) -> None:
        if text and len(insights) < 4:
            insights.append({"text": text, "evidence_refs": [ref for ref in refs if ref][:3] or fallback_refs})

    rotations: list[int] = []
    rotation_refs: list[str] = []
    perfect_pairs: list[dict[str, Any]] = []
    chat_quotes: list[tuple[str, str]] = []
    story_titles: list[str] = []
    contributions = 0
    solutions: list[tuple[str, str]] = []
    careers: list[str] = []
    for event in _dedupe_events(events):
        raw = event.get("raw_evidence", {}) if isinstance(event.get("raw_evidence"), dict) else {}
        context = event.get("context", {}) if isinstance(event.get("context"), dict) else {}
        summary = context.get("sessionSummary", {}) if isinstance(context.get("sessionSummary"), dict) else {}
        ref = str(event.get("id") or "")
        module = str(event.get("module"))
        if module == "deep_sea":
            level = int(raw.get("level", 0) or 0)
            if level == 1:
                successful, total = int(raw.get("successfulPairs", 0) or 0), int(raw.get("totalPairs", 0) or 0)
                if successful and total and successful == total:
                    perfect_pairs.append(event)
            elif level == 2:
                review = summary.get("levelTwoReview", {}) if isinstance(summary.get("levelTwoReview"), dict) else {}
                value = review.get("rotateCount", raw.get("adjustmentCount", 0)) if review else raw.get("adjustmentCount", 0)
                rotations.append(int(value or 0))
                rotation_refs.append(ref)
            elif level == 3:
                review = summary.get("levelThreeReview", {}) if isinstance(summary.get("levelThreeReview"), dict) else {}
                solution = str(review.get("solutionSummary", "")).strip() if review else ""
                if solution:
                    solutions.append((solution, ref))
        elif module == "chat":
            words = _clean_words(summary.get("childWords", ""))
            if _is_meaningful(words, str(raw.get("topicKey", ""))):
                chat_quotes.append((words, ref))
        elif module == "story":
            title = str(summary.get("storyTitle") or raw.get("storyTitle") or "").strip()
            if title and title not in story_titles:
                story_titles.append(title)
            contributions += max(0, int(raw.get("contributionCount", 0) or 0))
        elif module == "career":
            career = str(summary.get("careerName", "")).strip() or CAREER_NAMES.get(str(raw.get("taskKey", "")), "")
            if career and career not in careers:
                careers.append(career)
    if rotations:
        low, high = min(rotations), max(rotations)
        range_text = f"{low} 至 {high} 次" if low != high else f"{low} 次"
        if len(rotations) == 1:
            add(f"在需要反复试错的任务里孩子会持续调整：深海基地第二关“洋流电网”中，孩子旋转管件 {range_text} 后接通了起点与终点。", rotation_refs)
        else:
            add(f"在需要反复试错的任务里孩子会持续调整：深海基地第二关“洋流电网”的 {len(rotations)} 次挑战中，孩子共旋转管件 {range_text} 直到接通终点。", rotation_refs)
    if perfect_pairs:
        total = int(perfect_pairs[0].get("raw_evidence", {}).get("totalPairs", 4) or 4)
        if len(perfect_pairs) == 1:
            add(f"分类与配对类任务的完成度比较稳定：第一关“珊瑚公寓”一次完成了全部 {total} 组生态配对。", [str(item.get("id") or "") for item in perfect_pairs])
        else:
            add(f"分类与配对类任务的完成度比较稳定：第一关“珊瑚公寓”的 {len(perfect_pairs)} 次挑战每次都配对了全部 {total} 组生态关系。", [str(item.get("id") or "") for item in perfect_pairs])
    if chat_quotes:
        # 与报告智能体保持同一口径：引语按句读截到 40 字，原话自带引号时改用「」。
        samples = [_quote_child(_clip_phrase(words, 40)) for words, _ in chat_quotes[-3:]]
        relation_evidence = bool(solutions) or any(
            any(name in words for name in ("同学", "朋友", "老师", "爸爸", "妈妈", "家人", "伙伴"))
            for words, _ in chat_quotes
        )
        tail = "" if relation_evidence else "记录里的表达以短句陈述为主，还没有出现对他人想法的推测。"
        add(f"聊天中{child_name}愿意讲自己的生活：例如{'；'.join(samples)}。{tail}", [ref for _, ref in chat_quotes[-3:]])
    if solutions:
        solution, ref = solutions[-1]
        add(f"在出现角色分歧的情境里，孩子能在听取双方需要后给出兼顾办法：{_quote_child(_clip_phrase(solution, 60))}。", [ref])
    if story_titles or careers:
        parts = []
        if story_titles:
            titles = "、".join(f"《{title}》" for title in story_titles[-3:])
            parts.append(f"完成了 {len(story_titles)} 次故事共创（{titles}），共写下 {contributions} 个情节片段")
        if careers:
            parts.append(f"完成了 {len(careers)} 次职业体验（{'、'.join(careers)}）")
        add(f"跨活动的参与面已经展开：{child_name}{'；'.join(parts)}。", fallback_refs)
    return insights


def generate_internal_report(child_name: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    # 合并摘要类记录不参与维度归属和计数，判定口径与报告智能体保持一致。
    scoped = [event for event in events if _is_reportable_event(event)]
    # 整场是否走完，用来把单关记录标成“较完整记录”；调用方漏填时按会话兜底。
    completed_sessions = _completed_deep_sea_sessions(events)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in scoped:
        for candidate in event.get("intelligence_candidates", []):
            key = _key(str(candidate))
            if key:
                grouped[key].append(event)
    dimensions = []
    for key, name in DIMENSIONS.items():
        items = _dedupe_events(grouped.get(key, []))
        refs = list(dict.fromkeys(str(item.get("id")) for item in items if item.get("id")))
        modules = "、".join(sorted({MODULE_NAMES.get(str(item.get("module")), str(item.get("module"))) for item in items}))
        stories = [_dimension_event_summary(item, key) for item in items]
        facts = _dedupe_sentences(stories)
        # “较完整”只统计真正为这个维度写下内容的记录，与家长端卡片出现与否一致。
        contentful = [item for item, story in zip(items, stories) if str(story).strip()]
        strong = sum(_is_strong_record(item, completed_sessions) for item in contentful)
        if not items:
            analysis = "本阶段暂未收集到该维度的可回溯行为线索，因此不作判断。完成相关探索后，这里会结合真实行为生成观察提示。"
            adult = "暂无可观测数据。完成相关探索后，这里会结合孩子的真实行为生成观察提示。"
            child = "还没有可回看的探索记录。完成一次相关探索后，我会把你的真实表现写在这里。"
        else:
            if facts:
                analysis = (f"具体记录：{'；'.join(facts)}。{DIMENSION_ANGLE[key]}"
                            f"本阶段在{modules}中共留下 {len(items)} 条相关过程记录，其中 {strong} 条较完整。"
                            "这些内容只说明孩子在当时任务里采用了哪些做法，不等同于固定能力结论。")
            else:
                analysis = (f"本阶段在{modules}中共留下 {len(items)} 条参与记录，"
                            "但记录中只有话题入口或轮次统计，没有可复述的原话或操作细节，"
                            "因此本维度只登记参与情况，不据此比较表现差异。")
            adult = _adult_observation(key, items)
            child = _cumulative_child_story(items)
        dimensions.append({"key": key, "name": name, "status": "采集行为较少" if len(items) < 2 else ("证据丰富" if strong >= 2 else "证据均衡"), "evidence_refs": refs, "analysis": analysis, "adult_observation": adult, "child_story": child})
    refs = [str(event["id"]) for event in scoped if event.get("id")]
    insights = _cross_insights(scoped, child_name)
    if not insights:
        active = "、".join(MODULE_NAMES.get(module, module) for module in Counter(str(event.get("module")) for event in scoped)) or "活动模块"
        insights = [{"text": f"{child_name}在{active}中留下了可回溯记录。建议在不同情境中继续观察，不依据单次行为下结论。", "evidence_refs": refs[:3]}]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(), "rule": RULE, "analysis_version": ANALYSIS_VERSION, "dimensions": dimensions,
        "cross_insights": insights,
        "evidence_explanations": [_explain_event(event) for event in events],
        "recommendations": {"family": ["请孩子讲讲自己先做了什么、后来为什么改变。", "把体验变成低压力小游戏，允许先试再改。"], "teacher": ["记录孩子的第一种方案、反馈后的调整和最终结果。", "隔一至两周在新情境中复现相似任务。"]},
    }
