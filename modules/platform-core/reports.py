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
        text = f"{name}：孩子留下“{response[:140]}”" if response else f"{name}：孩子完成了这项互动"
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
            highlight_text = f" 精彩的一句是：“{highlight[:70]}”。" if highlight else ""
            return f"你和伙伴共创了《{title}》。故事梗概：{outline[:120].rstrip('。')}。{highlight_text}" if outline else f"你完成了《{title}》的共创，并写下了 {raw.get('contributionCount', 0)} 个故事片段。"
        if module == "chat":
            turns = raw.get("childTurns", []) if isinstance(raw.get("childTurns"), list) else []
            excerpts = [str(turn.get("text", "")).strip() for turn in turns if isinstance(turn, dict) and str(turn.get("text", "")).strip()]
            topic = str(raw.get("topicKey", "")).strip()
            words = str(summary.get("childWords", "")).strip()
            if words:
                people = [name for name in ("同学", "朋友", "老师", "爸爸", "妈妈", "家人", "伙伴") if name in words]
                relation = f"你还说清了自己对{'、'.join(people)}的关注和期待。" if people else "你把自己的感受和在意的事情说得很清楚。"
                activity = _chat_activity_source(raw)
                source = f" 你还通过{activity}留下了更具体的想法。" if activity else ""
                return f"这次聊天中，你说：“{words[:90]}”。{relation}{source}"
            if excerpts:
                words = excerpts[-1]
                people = [name for name in ("同学", "朋友", "老师", "爸爸", "妈妈", "家人", "伙伴") if name in words]
                relation = f"你还说清了自己对{'、'.join(people)}的关注和期待。" if people else "你把自己的感受和在意的事情说得很清楚。"
                activity = _chat_activity_source(raw)
                source = f" 你还通过{activity}留下了更具体的想法。" if activity else ""
                return f"这次聊天中，你说：“{words[:90]}”。{relation}{source}"
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
        review = f"最近的故事讲到：{'；'.join(text[:70] for text in outlines[-2:])}。" if outlines else ""
        highlights = [str(item.get("context", {}).get("sessionSummary", {}).get("childHighlight", "")).strip() for item in items if isinstance(item.get("context"), dict) and isinstance(item.get("context", {}).get("sessionSummary"), dict)]
        highlights = [text for text in highlights if text]
        highlight_text = f"精彩的一句是：“{highlights[-1][:70]}”。" if highlights else ""
        return f"你已经完成了 {len(items)} 次故事共创，共贡献了 {contributions} 个故事片段。{review}{highlight_text}"
    if module == "chat":
        turns = sum(max(0, int(raw.get("turnCount", 0) or 0)) for raw in raw_items)
        topics = list(dict.fromkeys(str(raw.get("topicKey", "")).strip() for raw in raw_items if str(raw.get("topicKey", "")).strip()))
        topic_text = f"你聊过“{'”“'.join(topics[-3:])}”。" if topics else ""
        excerpts = [str(turn.get("text", "")).strip() for raw in raw_items for turn in raw.get("childTurns", []) if isinstance(turn, dict) and str(turn.get("text", "")).strip()]
        excerpt_text = f"你分享过：“{'”“'.join(text[:45] for text in excerpts[-2:])}”。" if excerpts else ""
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
    raw = item.get("raw_evidence", {}) if isinstance(item.get("raw_evidence"), dict) else {}
    context = item.get("context", {}) if isinstance(item.get("context"), dict) else {}
    summary = context.get("sessionSummary", {}) if isinstance(context.get("sessionSummary"), dict) else {}
    if str(item.get("module")) == "chat":
        words = str(summary.get("childWords", "")).strip()
        people = [name for name in ("同学", "朋友", "老师", "爸爸", "妈妈", "家人", "伙伴") if name in words]
        source = _chat_activity_source(raw)
        source_text = f"（来自{source}活动）" if source else ""
        if dimension == "interpersonal":
            return (f"孩子提到{'、'.join(people)}并表达了对关系的关注：{words[:120]}{source_text}" if people else f"孩子参与了聊天，但现有记录没有可确认的他人观点或互动细节{source_text}")
        if dimension == "intrapersonal":
            return (f"孩子说出自己的感受、偏好、想法或期待：{words[:120]}{source_text}" if words else f"孩子完成了聊天，但现有记录没有可引用的自我表达{source_text}")
    if str(item.get("module")) == "career" and dimension == "intrapersonal":
        reflections = summary.get("mentorReflections", []) if isinstance(summary.get("mentorReflections"), list) else []
        answers = [str(value.get("answer", "")).strip() for value in reflections if isinstance(value, dict) and str(value.get("answer", "")).strip()]
        if answers: return f"在职业导师追问中，孩子回答：“{answers[-1][:140]}”，呈现了如何说明自己的想法、理由或感受"
    if str(item.get("module")) == "deep_sea":
        level = int(raw.get("level", 0) or 0)
        if level == 1 and dimension == "naturalistic": return "孩子依据栖息地和共生关系完成生态配对，呈现对生物特征与关系的辨认"
        if level == 1 and dimension == "logical": return "孩子比较配对条件并检查结果，呈现验证判断的过程"
        if level == 2 and dimension == "spatial": return "孩子通过摆放和旋转管件规划线路，呈现对位置、方向和连接关系的处理"
        if level == 2 and dimension == "logical": return "孩子检查断点和连通结果后调整方案，呈现排查和验证过程"
    if str(item.get("module")) != "deep_sea" or int(raw.get("level", 0) or 0) != 3:
        return str(item.get("behavior_summary", "")).rstrip("。；")
    review = summary.get("levelThreeReview", {}) if isinstance(summary.get("levelThreeReview"), dict) else {}
    solution = str(review.get("solutionSummary", "")).strip()
    utterances = review.get("childUtterances", []) if isinstance(review.get("childUtterances"), list) else []
    utterances = [str(value).strip() for value in utterances if str(value).strip()]
    if dimension == "linguistic":
        return f"孩子在调解中说：“{utterances[-1][:120]}”，呈现了如何组织调解语言" if utterances else "孩子完成了调解，但历史记录未保存逐字表达，语言维度不根据方案反推说话内容"
    return f"孩子选择的协调方案是：{solution[:140]}，呈现了如何回应双方需要" if solution else "孩子参与了双方需要的协调情境，但历史记录未保存具体方案"


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
            details = [f"调解表达：孩子说：“{utterances[-1][:120]}”" if utterances else "调解表达：这条历史记录未保存孩子当时的逐字表达。", f"方案选择：{solution[:140]}" if solution else "方案选择：这条历史记录未保存孩子当时选择的具体方案。"]
    elif module == "story":
        story_title = str(session.get("storyTitle", "")).strip() or str(raw.get("storyTitle", "")).strip() or "故事共创"
        synopsis = str(session.get("storySynopsis", "") or session.get("storyOutline", "")).strip()
        highlight = str(session.get("childHighlight", "")).strip()
        title, summary = f"故事共创：《{story_title}》", "孩子参与了故事情节的发展和结局创作。"
        details = [f"故事梗概：{synopsis[:160].rstrip('。')}。" if synopsis else "故事梗概：这条历史记录没有保存可复述的完整梗概。"]
        if highlight: details.append(f"精彩表达：“{highlight[:100]}”")
    elif module == "chat":
        words = str(session.get("childWords", "")).strip()
        title, summary = "聊天观察：真实表达", "孩子在聊天中说出了自己的感受、想法或关系期待。"
        details = [f"表达内容：孩子说：“{words[:120]}”" if words else "表达内容：这条历史记录没有保存可引用的聊天原文。", f"交流过程：本次共留下 {raw.get('turnCount', 0)} 轮表达。"]
        details.extend(f"活动来源：{detail}" for detail in _chat_activity_details(raw))
    elif module == "career":
        task_key = str(raw.get("taskKey", "")); career = str(session.get("careerName", "")).strip() or CAREER_NAMES.get(task_key, "职业")
        stages = session.get("stageTitles", []) if isinstance(session.get("stageTitles"), list) else []
        stages = [str(value).strip() for value in stages if str(value).strip()] or CAREER_STAGE_TITLES.get(task_key, [])
        title, summary = f"职业体验：{career}", f"孩子体验了{career}一天中的真实工作环节。"
        details = [f"体验内容：完成了{'、'.join(stages)}。" if stages else "体验内容：完成了本次职业情境中的任务。", f"过程表现：主动尝试 {raw.get('attemptCount', 0)} 次，调整 {raw.get('adjustmentCount', 0)} 次。"]
        reflections = session.get("mentorReflections", []) if isinstance(session.get("mentorReflections"), list) else []
        for reflection in reflections[-2:]:
            if isinstance(reflection, dict) and str(reflection.get("answer", "")).strip(): details.insert(-1, f"导师对话：孩子回答：“{str(reflection['answer']).strip()[:120]}”")
    return {"evidence_ref": item.get("id"), "title": title, "summary": summary, "details": details or ["本次活动已留下可回溯的过程记录。"]}


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
            examples = "；".join(_dimension_event_summary(item, key) for item in items[:4])
            analysis = f"本阶段在{modules}中收集到 {len(items)} 条可回溯行为记录，其中 {strong} 条为较完整记录。观察到：{examples}。这些记录反映的是孩子在当前情境中的做法，后续仍应在不同任务中继续观察其是否会主动重复、解释并调整这些方法。"
            adult = f"可以继续留意孩子在新任务里是否会再次出现“{str(items[0].get('behavior_summary', '')).rstrip('。')}”这样的做法，并邀请他说明原因。"
            child = _cumulative_child_story(items)
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
        "evidence_explanations": [_explain_event(event) for event in events],
        "recommendations": {"family": ["请孩子讲讲自己先做了什么、后来为什么改变。", "把体验变成低压力小游戏，允许先试再改。"], "teacher": ["记录孩子的第一种方案、反馈后的调整和最终结果。", "隔一至两周在新情境中复现相似任务。"]},
    }
