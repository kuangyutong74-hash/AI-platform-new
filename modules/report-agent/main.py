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
from reflection import QUESTION_SYSTEM_PROMPT, SUGGESTION_SYSTEM_PROMPT, evidence_briefs, fallback_questions, normalize_questions, normalize_suggestions

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

CAREER_NAMES = {
    "doctor": "社区医生", "firefighter": "消防员", "teacher": "小学教师",
    "chef": "餐厅厨师", "journalist": "报社记者", "animal_caretaker": "动物保护员",
}
CAREER_STAGE_TITLES = {
    "doctor": ["开诊台准备", "病人分诊", "问诊检查"],
    "firefighter": ["装备柜点检", "接警出动", "现场救援路径规划"],
    "teacher": ["布置晨间教室", "课堂管理", "和朵朵聊一聊"],
    "chef": ["后厨开档", "午餐炒饭流程", "出餐高峰应对"],
    "journalist": ["编辑部线索墙", "组织报道线索", "采访调查"],
    "animal_caretaker": ["晨间巡护打卡", "动物救助优先级", "动物健康检查"],
}
REPORT_RULE = "只统计行为频次、类型和原始上下文，不换算能力分数，不输出排名。"
REPORT_ANALYSIS_VERSION = "dimension-observation-v3"
PLATFORM_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
logger = logging.getLogger("report-agent")


def model_timeout() -> float:
    """Keep the complete three-stage report request within Core's deadline."""
    raw = os.getenv("REPORT_LLM_TIMEOUT") or platform_env().get("REPORT_LLM_TIMEOUT", "10")
    try:
        return min(8.0, max(3.0, float(raw)))
    except ValueError:
        return 8.0


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
    child_age: int = 0
    events: list[EvidenceEvent] = Field(default_factory=list)


class SuggestionRequest(BaseModel):
    dimension: dict[str, Any]
    child: dict[str, Any]
    evidence: dict[str, Any]
    questions: list[dict[str, Any]] = Field(default_factory=list)
    answers: list[dict[str, Any]] = Field(default_factory=list)


def canonical_key(key: str) -> str | None:
    normalized = SYNONYMS.get(key, key)
    return normalized if normalized in CANONICAL else None


def event_refs(events: list[EvidenceEvent]) -> list[str]:
    return list(dict.fromkeys(event.id for event in events if event.id))


def explain_event(event: EvidenceEvent) -> dict[str, Any]:
    """把机器采集字段转换为成人可以直接阅读的过程回顾。"""
    raw = event.raw_evidence
    context = event.context if isinstance(event.context, dict) else {}
    session = context.get("sessionSummary", {}) if isinstance(context.get("sessionSummary"), dict) else {}
    details: list[str] = []
    title = EVENT_NAMES.get(event.event_type, "探索过程回顾")
    summary_text = event.behavior_summary
    if event.event_type == "chat.observation-shared.v1":
        title = "聊天观察：真实表达"
        words = str(session.get("childWords", "")).strip()
        turns = raw.get("childTurns", []) if isinstance(raw.get("childTurns"), list) else []
        excerpts = [str(item.get("text", "")).strip() for item in turns if isinstance(item, dict) and str(item.get("text", "")).strip()]
        words = words or "；".join(excerpts[-2:])
        if words:
            details.append(f"表达内容：孩子说：“{words[:120]}”")
            summary_text = "孩子在聊天中说出了自己的感受、想法或关系期待。"
        else:
            details.append("表达内容：这条历史记录没有保存可引用的聊天原文。")
        details.append(f"交流过程：本次共留下 {raw.get('turnCount', len(excerpts))} 轮表达。")
    elif event.event_type == "career.task-completed.v1":
        task_key = str(raw.get("taskKey", "")).strip()
        career_name = str(session.get("careerName", "")).strip() or CAREER_NAMES.get(task_key, "职业")
        stages = session.get("stageTitles", []) if isinstance(session.get("stageTitles"), list) else []
        stages = [str(item).strip() for item in stages if str(item).strip()] or CAREER_STAGE_TITLES.get(task_key, [])
        title = f"职业体验：{career_name}"
        summary_text = f"孩子体验了{career_name}一天中的真实工作环节。"
        details = [f"体验内容：完成了{'、'.join(stages)}。" if stages else "体验内容：完成了本次职业情境中的任务。",
                   f"过程表现：主动尝试 {raw.get('attemptCount', 0)} 次，调整 {raw.get('adjustmentCount', 0)} 次，查看提示 {raw.get('hintCount', 0)} 次。"]
        reflections = session.get("mentorReflections", []) if isinstance(session.get("mentorReflections"), list) else []
        for reflection in reflections[-2:]:
            if isinstance(reflection, dict) and str(reflection.get("answer", "")).strip():
                details.insert(-1, f"导师对话：孩子回答：“{str(reflection['answer']).strip()[:120]}”")
    elif event.event_type == "deep-sea.spatial-task-completed.v1":
        level = int(raw.get("level", 0) or 0)
        if level == 1:
            review = session.get("levelOneReview", {}) if isinstance(session.get("levelOneReview"), dict) else {}
            pairs = review.get("matchedRelationships", []) if isinstance(review.get("matchedRelationships"), list) else []
            pairs = [str(item).strip() for item in pairs if str(item).strip()]
            title, summary_text = "深海基地第一关：珊瑚公寓", "孩子依据生物的栖息地和共生关系，为海洋生物安排住处。"
            details = [f"观察与判断：孩子完成了{'、'.join(pairs)}的生态关系配对。" if pairs else "观察与判断：孩子比较生物特征、栖息地和共生关系后完成配对。",
                       f"任务结果：成功配对 {raw.get('successfulPairs', 0)}/{raw.get('totalPairs', 4)} 组。"]
        elif level == 2:
            review = session.get("levelTwoReview", {}) if isinstance(session.get("levelTwoReview"), dict) else {}
            connected = review.get("connected")
            result = "接通了起点与终点" if connected is not False else "继续尝试接通线路"
            title, summary_text = "深海基地第二关：洋流电网", "孩子通过摆放、旋转和检查管件方向来规划洋流线路。"
            details = [f"建造过程：孩子组合管件、检查水流方向，最终{result}。",
                       f"调整记录：旋转或调整了 {review.get('rotateCount', raw.get('adjustmentCount', 0))} 次。"]
        elif level == 3:
            review = session.get("levelThreeReview", {}) if isinstance(session.get("levelThreeReview"), dict) else {}
            solution = str(review.get("solutionSummary", "")).strip() if isinstance(review, dict) else ""
            utterances = review.get("childUtterances", []) if isinstance(review, dict) else []
            utterances = [str(item).strip() for item in utterances if str(item).strip()] if isinstance(utterances, list) else []
            details = [f"调解表达：孩子说：“{utterances[-1][:120]}”" if utterances else "调解表达：这条历史记录未保存孩子当时的逐字表达。",
                       f"方案选择：{solution[:140]}" if solution else "方案选择：这条历史记录未保存孩子当时选择的具体方案。"]
            title, summary_text = "深海基地第三关：海洋议事厅", "孩子在角色分歧情境中完成了调解表达和方案选择。"
        else:
            details = ["完成了一次深海基地重建任务。"]
    elif event.event_type == "deep-sea.session-completed.v1":
        title, summary_text = "深海基地重建：完整探索", "孩子依次经历了生态配对、洋流线路建造和角色协商三类任务。"
        details = ["探索内容：完成珊瑚公寓、洋流电网和海洋议事厅的重建任务。", f"过程记录：完成 {raw.get('completedLevels', 0)}/{raw.get('totalLevels', 3)} 关，共调整 {raw.get('adjustmentCount', 0)} 次。"]
    elif event.event_type == "story.contribution-completed.v1":
        story_title = str(session.get("storyTitle", "")).strip() or str(raw.get("storyTitle", "")).strip() or "故事共创"
        synopsis = str(session.get("storySynopsis", "") or session.get("storyOutline", "")).strip()
        highlight = str(session.get("childHighlight", "")).strip()
        title, summary_text = f"故事共创：《{story_title}》", "孩子参与了故事情节的发展和结局创作。"
        details = [f"故事梗概：{synopsis[:160].rstrip('。')}。" if synopsis else "故事梗概：这条历史记录没有保存可复述的完整梗概。"]
        if highlight:
            details.append(f"精彩表达：“{highlight[:100]}”")
        details.append(f"共创过程：孩子贡献了 {raw.get('contributionCount', 0)} 个故事片段。")
    if not details:
        details = ["系统保留了这次活动中的关键行为过程，供家长和老师后续对照观察。"]
    return {
        "evidence_ref": event.id,
        "title": title,
        "summary": summary_text,
        "details": details,
    }


def dimension_event_story(event: EvidenceEvent, dimension: str) -> str:
    """按智能维度解释同一事件，避免把语言表达和人际选择写成同一结论。"""
    if event.module == "chat":
        summary = event.context.get("sessionSummary", {}) if isinstance(event.context, dict) else {}
        words = str(summary.get("childWords", "")).strip() if isinstance(summary, dict) else ""
        people = [name for name in ("同学", "朋友", "老师", "爸爸", "妈妈", "家人", "伙伴") if name in words]
        if dimension == "interpersonal":
            return (f"孩子在聊天中提到{'、'.join(people)}，并说：“{words[:120]}”。人际维度只观察这段表达中对他人和关系的关注。"
                    if people else "孩子参与了聊天，但现有记录没有保存可确认的他人观点或互动细节，因此人际维度不根据个人感受反推关系表现。")
        if dimension == "intrapersonal":
            return (f"孩子在聊天中说：“{words[:120]}”。内省维度观察的是孩子如何说出自己的感受、偏好、想法或期待。"
                    if words else "孩子完成了聊天，但现有记录没有保存可引用的自我表达，因此内省维度不作进一步推断。")
    if event.module == "career" and dimension == "intrapersonal":
        summary = event.context.get("sessionSummary", {}) if isinstance(event.context, dict) else {}
        reflections = summary.get("mentorReflections", []) if isinstance(summary, dict) and isinstance(summary.get("mentorReflections"), list) else []
        answers = [str(item.get("answer", "")).strip() for item in reflections if isinstance(item, dict) and str(item.get("answer", "")).strip()]
        if answers:
            return f"在职业导师追问中，孩子回答：“{answers[-1][:140]}”。这条记录呈现的是孩子如何说明自己的想法、理由或感受。"
    if event.module == "deep_sea":
        level = int(event.raw_evidence.get("level", 0) or 0)
        summary = event.context.get("sessionSummary", {}) if isinstance(event.context, dict) else {}
        if level == 1:
            review = summary.get("levelOneReview", {}) if isinstance(summary, dict) else {}
            pairs = review.get("matchedRelationships", []) if isinstance(review, dict) else []
            pairs = [str(item).strip() for item in pairs if str(item).strip()] if isinstance(pairs, list) else []
            if dimension == "naturalistic":
                pair_text = f"：{'、'.join(pairs)}" if pairs else ""
                return f"孩子依据栖息地和共生关系完成生态配对{pair_text}，自然观察维度关注其对生物特征与关系的辨认。"
            if dimension == "logical":
                return "孩子比较配对条件并检查结果，逻辑维度关注其如何验证判断，而不是生物知识本身。"
        if level == 2:
            if dimension == "spatial":
                return "孩子摆放并旋转管件来规划洋流线路，空间维度关注位置、方向和连接关系。"
            if dimension == "logical":
                return "孩子检查线路断点与连通结果后调整方案，逻辑维度关注排查和验证过程。"
    if event.module != "deep_sea" or int(event.raw_evidence.get("level", 0) or 0) != 3:
        return child_story_for_event(event)
    summary = event.context.get("sessionSummary", {}) if isinstance(event.context, dict) else {}
    review = summary.get("levelThreeReview", {}) if isinstance(summary, dict) else {}
    solution = str(review.get("solutionSummary", "")).strip() if isinstance(review, dict) else ""
    utterances = review.get("childUtterances", []) if isinstance(review, dict) else []
    utterances = [str(item).strip() for item in utterances if str(item).strip()] if isinstance(utterances, list) else []
    if dimension == "linguistic":
        return f"在海洋议事厅的调解中，孩子说：“{utterances[-1][:120]}”。这条记录呈现的是孩子如何用语言回应双方、组织调解意见。" if utterances else "孩子完成了海洋议事厅调解，但这条历史记录没有保存逐字表达，因此语言智能不根据所选方案反推说话内容。"
    if dimension == "interpersonal":
        return f"在海洋议事厅中，孩子选择的协调方案是：{solution[:140].rstrip('。')}。这条记录呈现的是方案如何回应双方需要。" if solution else "孩子完成了海洋议事厅调解，但这条历史记录没有保存具体方案，因此人际智能只确认参与了双方需要的协调情境。"
    return child_story_for_event(event)


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
            people = [name for name in ("同学", "朋友", "老师", "爸爸", "妈妈", "家人", "伙伴") if name in words]
            relation = f"你还说清了自己对{'、'.join(people)}的关注和期待。" if people else "你把自己的感受和在意的事情说得很清楚。"
            return f"这次聊天中，你说：“{words[:90]}”。{relation}"
        if topic:
            return f"这次聊天里，你围绕“{topic}”进行了 {raw.get('turnCount', 0)} 轮表达。智能体只记录了这次真实聊过的内容。"
    if event.module == "story":
        title = title or str(summary.get("storyTitle", "")).strip() or str(raw.get("storyTitle", "")).strip() or "这次故事"
        outline = str(summary.get("storySynopsis", "") or summary.get("storyOutline", "")).strip()
        highlight = str(summary.get("childHighlight", "")).strip()
        ideas = summary.get("childIdeas", []) if isinstance(summary, dict) else []
        ideas = [str(item).strip() for item in ideas if str(item).strip()] if isinstance(ideas, list) else []
        detail = outline or artifact_summary.removeprefix("故事讲到：").strip()
        if detail:
            highlight_text = f" 精彩的一句是：“{highlight[:70]}”。" if highlight else (f" 你提出过：“{ideas[-1][:60]}”。" if ideas else "")
            return f"你和伙伴共创了《{title}》。故事梗概：{detail[:120].rstrip('。')}。{highlight_text}".strip()
        return f"你完成了《{title}》的共创，并为故事写下了 {raw.get('contributionCount', 0)} 个片段。"
    if event.module == "deep_sea":
        level = int(raw.get("level", 0))
        if level == 1:
            review = summary.get("levelOneReview", {}) if isinstance(summary, dict) else {}
            pairs = review.get("matchedRelationships", []) if isinstance(review, dict) else []
            pairs = [str(item).strip() for item in pairs if str(item).strip()] if isinstance(pairs, list) else []
            successful = int(raw.get("successfulPairs", 0))
            total = int(raw.get("totalPairs", 4))
            accuracy = round(float(raw.get("accuracyPercent", successful / max(total, 1) * 100)))
            checks = raw.get("checkAttempts")
            check_text = f"，一共检查了 {checks} 次" if checks is not None else ""
            result = "全部配对成功" if successful == total else "还没有全部配对成功"
            if pairs:
                return f"在第一关“珊瑚公寓”里，你根据栖息地和共生关系，为{'、'.join(pairs)}找到了合适的位置；{result}{check_text}。"
            return f"在第一关“珊瑚公寓”里，你观察生物的栖息地和共生关系来安排住处，成功完成 {successful}/{total} 组配对（{result}）{check_text}。"
        if level == 2:
            review = summary.get("levelTwoReview", {}) if isinstance(summary, dict) else {}
            connected = review.get("connected") if isinstance(review, dict) else None
            rotations = int(review.get("rotateCount", raw.get("adjustmentCount", 0)) or 0) if isinstance(review, dict) else int(raw.get("adjustmentCount", 0) or 0)
            result = "接通了起点和终点" if connected is not False else "继续寻找接通线路的办法"
            return f"在第二关“洋流电网”里，你摆放并旋转管件，检查水流方向，经过 {rotations} 次旋转调整后{result}。"
        if level == 3:
            review = summary.get("levelThreeReview", {}) if isinstance(summary, dict) else {}
            solution = str(review.get("solutionSummary", "")).strip() if isinstance(review, dict) else ""
            utterances = review.get("childUtterances", []) if isinstance(review, dict) else []
            utterances = [str(item).strip() for item in utterances if str(item).strip()] if isinstance(utterances, list) else []
            if solution:
                quote = f" 你在协商中说：“{utterances[-1][:90]}”。" if utterances else ""
                return f"在第三关“海洋议事厅”里，你听取双方需要，并提出了协调办法：{solution[:120].rstrip('。')}。{quote}".strip()
            return "在第三关“海洋议事厅”里，你听取不同角色的需要，选择回应方式并尝试提出协调方案。"
        return f"在深海任务中，你完成了 {raw.get('completedLevels', raw.get('level', 0))} 个关卡，并根据反馈调整了 {raw.get('adjustmentCount', 0)} 次。"
    if event.module == "career":
        task_key = str(raw.get("taskKey", "")).strip()
        career_name = str(summary.get("careerName", "")).strip() if isinstance(summary, dict) else ""
        if not career_name and title:
            career_name = title.removesuffix("的一天").strip()
        career_name = career_name or CAREER_NAMES.get(task_key, "这次职业")
        stage_titles = summary.get("stageTitles", []) if isinstance(summary, dict) else []
        if not isinstance(stage_titles, list) or not stage_titles:
            stage_titles = CAREER_STAGE_TITLES.get(task_key, [])
        stage_titles = [str(item).strip() for item in stage_titles if str(item).strip()]
        if stage_titles:
            return f"在“{career_name}”体验里，你完成了{'、'.join(stage_titles)}，走完了这个职业一天里的几项真实任务。"
        if artifact_summary:
            return f"在“{career_name}”体验里，{artifact_summary.rstrip('。')}。"
        return f"你完成了一次“{career_name}”职业体验。"
    if artifact_summary:
        return f"这次探索留下的真实记录是：{artifact_summary}"
    return "这次体验已经完成，但目前保存的记录还不足以写出这颗星的专属发现。"


def child_story_for_events(events: list[EvidenceEvent]) -> str:
    """把同一颗星的全部历史体验压缩成儿童可读的累计反馈。"""
    if not events:
        return "还没有可回看的探索记录。去对应的大陆完成一次游戏后，我会把你的真实表现写在这里。"
    if len(events) == 1:
        return child_story_for_event(events[0])

    if any(event.module == "deep_sea" for event in events) and all(event.module == "chat" or (event.module == "deep_sea" and int(event.raw_evidence.get("level", 0) or 0) == 3) for event in events):
        chats = [event for event in events if event.module == "chat"]
        negotiations = [event for event in events if event.module == "deep_sea"]
        parts = [child_story_for_event(event).rstrip("。") for event in events[-3:]]
        lead = f"你留下了 {len(chats)} 次聊天交流和 {len(negotiations)} 次议事厅协商记录。"
        return f"{lead}{'；'.join(parts)}。"

    if all(event.module == "story" for event in events):
        contributions = sum(max(0, int(event.raw_evidence.get("contributionCount", 0) or 0)) for event in events)
        titles = []
        for event in events:
            artifacts = event.context.get("artifacts", []) if isinstance(event.context, dict) else []
            title = next((str(item.get("title", "")).strip() for item in artifacts if isinstance(item, dict) and item.get("title")), "")
            if title and title not in titles:
                titles.append(title)
        title_text = ""
        if titles:
            shown = "、".join(f"《{title}》" for title in titles[-3:])
            title_text = f"你创作过{shown}{f'等 {len(titles)} 个故事' if len(titles) > 3 else ''}。"
        outlines = []
        for event in events:
            summary = event.context.get("sessionSummary", {}) if isinstance(event.context, dict) else {}
            outline = str(summary.get("storySynopsis", "") or summary.get("storyOutline", "")).strip() if isinstance(summary, dict) else ""
            if outline and outline not in outlines:
                outlines.append(outline)
        highlights = [str(event.context.get("sessionSummary", {}).get("childHighlight", "")).strip() for event in events if isinstance(event.context, dict) and isinstance(event.context.get("sessionSummary"), dict)]
        highlights = [text for text in highlights if text]
        outline_text = f"最近的故事讲到：{'；'.join(text[:70] for text in outlines[-2:])}。" if outlines else ""
        highlight_text = f"精彩的一句是：“{highlights[-1][:70]}”。" if highlights else ""
        return f"你已经完成了 {len(events)} 次故事共创，共贡献了 {contributions} 个故事片段。{title_text}{outline_text}{highlight_text}"

    if all(event.module == "chat" for event in events):
        turns = sum(max(0, int(event.raw_evidence.get("turnCount", 0) or 0)) for event in events)
        topics: list[str] = []
        excerpts: list[str] = []
        for event in events:
            topic = str(event.raw_evidence.get("topicKey", "")).strip()
            if topic and topic not in topics:
                topics.append(topic)
            child_turns = event.raw_evidence.get("childTurns", [])
            if isinstance(child_turns, list):
                for turn in child_turns:
                    text = str(turn.get("text", "")).strip() if isinstance(turn, dict) else ""
                    if text and text not in excerpts:
                        excerpts.append(text)
            summary = event.context.get("sessionSummary", {}) if isinstance(event.context, dict) else {}
            words = str(summary.get("childWords", "")).strip() if isinstance(summary, dict) else ""
            if words and words not in excerpts:
                excerpts.append(words)
        details = []
        if topics:
            details.append(f"你聊过“{'”“'.join(topics[-3:])}”{f'等 {len(topics)} 个主题' if len(topics) > 3 else ''}")
        if excerpts:
            details.append(f"你还说过：“{'”“'.join(text[:42] for text in excerpts[-2:])}”")
        detail_text = "，".join(details)
        people = [name for name in ("同学", "朋友", "老师", "爸爸", "妈妈", "家人", "伙伴") if any(name in text for text in excerpts)]
        relation_text = f"你在分享中提到了{'、'.join(people)}，也说出了自己对这些关系的感受和期待。" if people else ""
        return f"你已经完成了 {len(events)} 次聊天。{detail_text + '。' if detail_text else ''}{relation_text}"

    if all(event.module == "career" for event in events):
        reviews = list(dict.fromkeys(child_story_for_event(event).rstrip("。") for event in events))
        return f"你已经完成了 {len(events)} 次职业体验。{'；'.join(reviews[-3:])}。之前体验过的职业内容也都收藏在这颗星里。"

    examples = "；".join(child_story_for_event(event).rstrip("。；") for event in events[-3:])
    return f"你已经完成了 {len(events)} 次相关探索。最近的真实记录包括：{examples}。这颗星也保留着之前的全部互动。"


def adult_observation_for_dimension(key: str, items: list[EvidenceEvent]) -> str:
    """Create dimension-specific transfer observations anchored in real evidence."""
    if not items:
        return "暂无可观测数据。完成相关探索后，这里会结合孩子的真实行为生成观察提示。"
    latest = items[-1]
    summary = latest.context.get("sessionSummary", {}) if isinstance(latest.context, dict) else {}
    raw = latest.raw_evidence
    story_title = str(summary.get("storyTitle") or raw.get("storyTitle") or "这次故事").strip()
    words = str(summary.get("childWords", "")).strip()
    level = int(raw.get("level", 0) or 0)
    task_anchor = story_title if latest.module == "story" else (({1:"珊瑚公寓",2:"洋流电网",3:"海洋议事厅"}.get(level) or "这次深海任务") if latest.module == "deep_sea" else str(summary.get("careerName") or "这次任务"))
    if key == "linguistic":
        anchor = f"《{story_title}》" if latest.module == "story" else (f"孩子说过的“{words[:24]}”" if words else task_anchor)
        observations = [
            f"请孩子把{anchor}讲给没听过的人，观察他会怎样交代人物、起因和结果",
            "邀请孩子为同一段情节换一种开头或结尾，留意他如何保持前后连贯",
            "听孩子解释为什么选这个词或这句对白，记录他能否说出表达意图",
            "一至两周后给出三个关键词，请孩子再编一段，比较叙述是否更完整具体",
        ]
    elif key == "logical":
        observations = [
            f"换一个与“{task_anchor}”规则不同的小任务，观察孩子会先比较条件还是直接尝试",
            "请孩子预测一种做法可能得到什么结果，再实际验证，留意预测与检查是否对应",
            "结果不符合预期时，观察孩子会检查哪一步，以及能否只改变一个条件再试",
            "一至两周后再给相似问题，请孩子说出判断依据，比较推理步骤是否更清楚",
        ]
    elif key == "spatial":
        observations = [
            f"参照“{task_anchor}”换一套拼搭材料，观察孩子如何处理位置、方向和连接关系",
            "请孩子先口头描述或画出摆放方案，再动手搭建，对照计划与成品的变化",
            "把一个部件旋转或挪位，观察孩子能否发现变化并说明哪里需要重新连接",
            "一至两周后请孩子凭记忆重建简单布局，留意他使用了哪些空间线索",
        ]
    elif key == "interpersonal":
        people = [name for name in ("同学","朋友","老师","爸爸","妈妈","家人","伙伴") if name in words]
        relation = "、".join(people) or "不同角色"
        observations = [
            f"在谈到{relation}时，先请孩子分别说说每个人想要什么，观察他是否区分不同需要",
            "出现小分歧时，请孩子先复述对方的话再回应，留意他是否抓住对方真正关心的事",
            "邀请孩子提出两种兼顾双方的办法，并说说每种办法可能让谁满意或为难",
            "一至两周后在新的合作活动中观察，孩子是否会主动询问、轮流或调整分工",
        ]
    elif key == "intrapersonal":
        observations = [
            "任务开始前请孩子说说最想做和最担心的部分，留意他能否描述自己的偏好与感受",
            "遇到卡住时，用“你现在需要提示、休息还是再试一次”帮助他辨认自己的状态",
            "完成后请孩子选出最满意和最想修改的一步，并说明判断来自结果还是个人感受",
            "一至两周后遇到相似困难时，观察孩子是否会主动采用自己选过的调节办法",
        ]
    else:
        observations = [
            f"把“{task_anchor}”中的分类线索换成身边物品或常见生物，观察孩子会依据哪些特征归类",
            "请孩子解释两个对象为什么放在一起，再找一个不适合的例子说明区别",
            "发现新信息与原判断不一致时，观察孩子会保留、修改还是重新建立分类标准",
            "一至两周后到户外或看图鉴时，再观察孩子是否会主动比较特征与关系",
        ]
    return "；".join(observations) + "。"


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
                f"具体记录：{'；'.join(dimension_event_story(item, key).rstrip('。；') for item in items[:4])}。"
                f"本阶段在{'、'.join(modules)}中共留下{len(items)}条相关过程记录，其中{strong}条较完整。"
                "这些内容只说明孩子在当时任务里采用了哪些做法，不等同于固定能力结论。"
                if items else "本阶段暂未收集到该维度的可回溯行为线索，因此不作判断。"
            )
            observation = adult_observation_for_dimension(key, items)
            child_story = child_story_for_events(items)
            dimensions.append({"key": key, "name": name, "status": status, "evidence_refs": refs, "analysis": analysis, "adult_observation": observation, "child_story": child_story})
        active = [MODULE_NAMES.get(name, name) for name, count in Counter(event.module for event in events).items() if count]
        refs = event_refs(events)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(), "rule": REPORT_RULE, "analysis_version": REPORT_ANALYSIS_VERSION,
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
用第二人称和一至三句儿童能读懂的话，综合该维度全部历史事件：必须说明累计体验次数与累计互动结果，并尽量点明不同的真实话题、故事名、任务名、孩子原话或实际调整次数。
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
        base_url = os.getenv("REPORT_LLM_BASE_URL") or os.getenv("AI_BASE_URL") or os.getenv("AI_API_BASE") or os.getenv("ZHIPUAI_BASE_URL") or os.getenv("ZHIPU_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or local.get("REPORT_LLM_BASE_URL") or local.get("AI_BASE_URL") or local.get("AI_API_BASE") or local.get("ZHIPUAI_BASE_URL") or local.get("ZHIPU_BASE_URL") or local.get("DEEPSEEK_BASE_URL", "")
        api_key = os.getenv("REPORT_LLM_API_KEY") or os.getenv("AI_API_KEY") or os.getenv("ZHIPUAI_API_KEY") or os.getenv("ZHIPU_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or local.get("REPORT_LLM_API_KEY") or local.get("AI_API_KEY") or local.get("ZHIPUAI_API_KEY") or local.get("ZHIPU_API_KEY") or local.get("DEEPSEEK_API_KEY", "")
        model = os.getenv("REPORT_LLM_MODEL") or os.getenv("AI_MODEL") or os.getenv("ZHIPUAI_MODEL") or os.getenv("ZHIPU_MODEL") or os.getenv("DEEPSEEK_MODEL") or local.get("REPORT_LLM_MODEL") or local.get("AI_MODEL") or local.get("ZHIPUAI_MODEL") or local.get("ZHIPU_MODEL") or local.get("DEEPSEEK_MODEL", "")
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
            with urlrequest.urlopen(http_request, timeout=model_timeout()) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("报告模型请求失败") from exc
        content = result["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return json.loads(str(content).strip().removeprefix("```json").removesuffix("```").strip())

    def ask_json(self, system_prompt: str, data: dict[str, Any], temperature: float = 0.2) -> dict[str, Any]:
        endpoint = self.base_url if self.base_url.endswith("/chat/completions") else f"{self.base_url}/chat/completions"
        payload = {"model":self.model,"temperature":temperature,"response_format":{"type":"json_object"},"messages":[{"role":"system","content":system_prompt},{"role":"user","content":json.dumps(data,ensure_ascii=False)}]}
        request = urlrequest.Request(endpoint,data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"},method="POST")
        try:
            with urlrequest.urlopen(request, timeout=model_timeout()) as response:
                result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            return json.loads(str(content).strip().removeprefix("```json").removesuffix("```").strip())
        except (error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("报告模型请求失败") from exc

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
            with urlrequest.urlopen(http_request, timeout=model_timeout()) as response:
                result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            return json.loads(str(content).strip().removeprefix("```json").removesuffix("```").strip())
        except (error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("维度深描模型请求失败") from exc


def apply_dimension_expansion(report: dict[str, Any], expansion: dict[str, Any], events: list[EvidenceEvent] | None = None) -> dict[str, Any]:
    supplied = {canonical_key(str(item.get("key", ""))): item for item in expansion.get("dimensions", []) if isinstance(item, dict)}
    protected = {key for event in (events or []) if len(event.intelligence_candidates) > 1 for key in event.intelligence_candidates}
    for dimension in report.get("dimensions", []):
        item = supplied.get(dimension.get("key"))
        if not item or not dimension.get("evidence_refs"):
            continue
        clean_list = lambda value: [str(part).strip().rstrip("。；;，,") for part in value if str(part).strip()] if isinstance(value, list) else []
        facts = clean_list(item.get("facts"))[:4]
        interpretations = clean_list(item.get("interpretations"))[:4]
        limits = clean_list(item.get("limits"))[:2]
        observation_items = clean_list(item.get("adult_observations"))
        if facts and interpretations and limits and dimension.get("key") not in protected:
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
            # 同一事件跨维度时必须使用维度专属的确定性解释，避免模型把
            # 人际、内省、逻辑等页面复写成同一段话。
            "analysis": fallback_item["analysis"],
            # 延伸观察必须由本维度的真实事件确定性生成。模型输出可能把六个
            # 维度写成同一套通用模板，因此不能在最终合并时覆盖专属观察。
            "adult_observation": fallback_item["adult_observation"],
            # 星星反馈必须稳定覆盖全部历史事件，不允许模型退化成只复述一条。
            "child_story": fallback_item["child_story"],
        })
    level_three_refs = {event.id for event in events if event.id and event.module == "deep_sea" and int(event.raw_evidence.get("level", 0) or 0) == 3}
    if level_three_refs:
        fallback_by_key = {item["key"]: item for item in fallback["dimensions"]}
        for dimension in dimensions:
            if dimension["key"] in {"linguistic", "interpersonal"} and level_three_refs.intersection(dimension["evidence_refs"]):
                dimension["analysis"] = fallback_by_key[dimension["key"]]["analysis"]
    cross_insights = []
    for item in candidate.get("cross_insights", []):
        if isinstance(item, dict):
            refs = [ref for ref in item.get("evidence_refs", []) if ref in valid_refs]
            text = str(item.get("text", "")).strip()
            if text and refs:
                cross_insights.append({"text": text, "evidence_refs": refs})
    if not cross_insights:
        cross_insights = fallback["cross_insights"]
    # 过程回顾由确定性规则从原始证据生成，避免模型把不同活动都改写成
    # “用时/调整次数/成功率”的同一种说明。
    evidence_explanations = fallback["evidence_explanations"]
    supplied = candidate.get("recommendations", {}) if isinstance(candidate.get("recommendations"), dict) else {}
    def advice_list(value: Any, fallback_items: list[str]) -> list[str]:
        values = value if isinstance(value, list) else [value] if isinstance(value, str) else []
        clean = [str(item).strip() for item in values if str(item).strip()]
        return (clean + [item for item in fallback_items if item not in clean])[:6]
    family = advice_list(supplied.get("family"), fallback["recommendations"]["family"])
    teacher = advice_list(supplied.get("teacher"), fallback["recommendations"]["teacher"])
    if teacher == family: teacher = fallback["recommendations"]["teacher"]
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "rule": REPORT_RULE, "analysis_version": REPORT_ANALYSIS_VERSION, "dimensions": dimensions, "cross_insights": cross_insights, "evidence_explanations": evidence_explanations, "recommendations": {"family": family, "teacher": teacher}}


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
        except Exception:
            logger.exception("第一阶段报告生成失败，改用规则报告")
            report = RuleAnalyzer().analyze(report_request.events)
        dimensions = evidence_briefs(report, report_request.events)
        # 报告页是同步打开链路，不能再串行等待两个额外模型请求。
        # 维度追问使用同一批真实证据确定性生成，确保页面稳定出现且不虚构事实。
        report["questions"] = fallback_questions(report_request.child_name, dimensions)
        return report
    report = RuleAnalyzer().analyze(report_request.events)
    dimensions = evidence_briefs(report, report_request.events)
    report["questions"] = fallback_questions(report_request.child_name, dimensions)
    return report


@app.post("/api/report/suggestions")
def generate_suggestions(request: SuggestionRequest) -> dict[str, Any]:
    child_name = str(request.child.get("childName") or "孩子")
    analyzer = LLMAnalyzer.from_environment()
    if not analyzer:
        return normalize_suggestions({}, child_name, request.answers, request.questions, request.dimension)
    try:
        result = analyzer.ask_json(SUGGESTION_SYSTEM_PROMPT, request.model_dump())
        return normalize_suggestions(result, child_name, request.answers, request.questions, request.dimension)
    except Exception:
        logger.exception("专属建议生成失败，使用安全回退建议")
        return normalize_suggestions({}, child_name, request.answers, request.questions, request.dimension)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8030, reload=False)
