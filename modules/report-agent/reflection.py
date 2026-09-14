from __future__ import annotations

from typing import Any


QUESTION_SYSTEM_PROMPT = """你是天赋魔法书的观察星章助手，负责为家长生成“星章的提问信”。只能依据输入 child 与 dimensions；evidence_brief 必须逐字引用，不得虚构、改写或推断。只返回一个 JSON 对象，不要 Markdown 或说明文字。
输出结构：{"lead_note":"","global_questions":[],"dimension_questions":[]}。
lead_note 40字以内，包含孩子名字，说明家长回答会与魔法书观察放在一起形成专属建议，不得出现问卷、测试、评估。
dimension_questions 从所有具有真实 evidence_brief 的维度中选1至2题，包含状态为“采集行为较少”的维度，并优先具体证据。每题保留真实 key、evidence_ref、module、evidence_brief；lead 8字以内且以破折号结尾，question 30字以内，只问家庭中家长能亲眼看到的事；提供3至4个互斥、口语化、8字以内选项，可含“没注意过”；allow_text=true，placeholder 20字以内。
global_questions 恰好3题，category依次为“家庭陪伴”“期待”“在意”；每题必须含孩子名字，lead 8字以内，question 30字以内，3至4个互斥无评价选项，allow_text=true，placeholder 20字以内。
不得比较、诊断、排名、打分或制造焦虑。"""


SUGGESTION_SYSTEM_PROMPT = """你是天赋魔法书的观察星章助手。综合平台证据与家长回答，为一个维度生成专属建议。只返回 JSON：{"consistency":{"conclusion":"一致 | 仅平台显现 | 仅家庭显现 | 证据不足","text":""},"family_suggestions":[],"teacher_suggestions":[],"transition_note":""}。
只能依据 evidence 与 answers；未作答或“没注意过”按无补充处理。consistency.text 必须同时引用家长选择原词和一条证据事实；证据不足时明确说明。family_suggestions 4至6条，每条给出谁、场景、动作和一句示例话术，45字以内，含话术最多60字。teacher_suggestions 3至5条，具体可执行，不照抄家庭安排。transition_note 30字以内且含孩子名字。不得虚构、诊断、评分、排名、比较或制造焦虑。"""


FOLLOWUP_SYSTEM_PROMPT = """你是观察星章助手。家长补充若已明确，返回 {"need_followup":false}；仅在“还行”“看情况”等含义模糊时返回 {"need_followup":true,"followup":"20字以内、轻松不施压的追问"}。只返回JSON，每封信最多追问一次。"""


MODULE_NAMES = {"story":"故事共创","chat":"聊天观察","deep_sea":"深海基地重建","career":"职业模拟器"}
QUESTION_VERSION = "module-bank-v1"

MODULE_QUESTION_BANK = {
    "story": {"lead":"聊聊这次故事","question":"孩子平时讲故事时，通常怎样展开想法？","options":["先想人物","先想情节","边讲边想","很少讲故事"],"placeholder":"比如最近讲过的一个故事"},
    "chat": {"lead":"聊聊日常表达","question":"孩子遇到在意的事，通常会怎样告诉您？","options":["主动说出来","问了才会说","边做边说","暂时不想说"],"placeholder":"可以写下当时的一句话"},
    "deep_sea": {"lead":"聊聊动手尝试","question":"碰到需要反复尝试的任务时，孩子通常怎么做？","options":["自己换办法","请人给提示","先停一会儿","容易放弃"],"placeholder":"比如拼搭、解题或做手工"},
    "career": {"lead":"聊聊面对任务","question":"面对一个没做过的新任务，孩子通常怎样开始？","options":["先观察再做","马上动手试","先问清步骤","需要陪着做"],"placeholder":"可以写下最近的一次尝试"},
}


def evidence_briefs(report: dict[str, Any], events: list[Any]) -> list[dict[str, Any]]:
    by_id = {str(event.id): event for event in events if getattr(event, "id", None)}
    explanations = {str(item.get("evidence_ref")): item for item in report.get("evidence_explanations", []) if isinstance(item, dict)}
    dimensions = []
    for dimension in report.get("dimensions", []):
        briefs = []
        for ref in dimension.get("evidence_refs", []):
            event = by_id.get(str(ref))
            if not event:
                continue
            text = str(explanations.get(str(ref), {}).get("summary") or event.behavior_summary).strip()
            briefs.append({"evidence_ref":str(ref),"module":event.module,"text":text[:20]})
        dimensions.append({"key":dimension.get("key"),"status":dimension.get("status"),"analysis":dimension.get("analysis", ""),"evidence_brief":briefs})
    return dimensions


def fallback_questions(child_name: str, dimensions: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = []
    seen_modules = set()
    for item in dimensions:
        for brief in reversed(item.get("evidence_brief", [])):
            module = brief.get("module")
            if module in MODULE_QUESTION_BANK and module not in seen_modules:
                eligible.append((item, brief))
                seen_modules.add(module)
    eligible.sort(key=lambda pair: list(MODULE_QUESTION_BANK).index(pair[1]["module"]))
    dimension_questions = []
    for index, (item, brief) in enumerate(eligible, 1):
        preset = MODULE_QUESTION_BANK[brief["module"]]
        dimension_questions.append({"id":f"d{index}","key":item["key"],"evidence_ref":brief["evidence_ref"],"module":brief["module"],"evidence_brief":brief["text"],**preset,"allow_text":True})
    return {
        "question_version":QUESTION_VERSION,
        "lead_note":f"也想听听您眼中的{child_name}。这些日常片段会和游戏记录一起写进建议。"[:40],
        "global_questions":[
            {"id":"g1","category":"家庭陪伴","lead":"关于陪伴——","question":f"平时谁陪{child_name}探索得更多？"[:30],"options":["爸爸妈妈","祖辈家人","大家轮流","其他陪伴"],"allow_text":True,"placeholder":"周末最常一起做什么？"},
            {"id":"g2","category":"期待","lead":"关于期待——","question":f"最希望{child_name}在哪方面多尝试？"[:30],"options":["表达想法","动手解决","理解伙伴","认识自己"],"allow_text":True,"placeholder":"写下一件期待的小事"},
            {"id":"g3","category":"在意","lead":"最近在意——","question":f"最近最想多了解{child_name}什么？"[:30],"options":["兴趣变化","遇难反应","合作方式","还没想好"],"allow_text":True,"placeholder":"可以写下最近的观察"},
        ],
        "dimension_questions":dimension_questions,
    }


def normalize_questions(candidate: dict[str, Any], child_name: str, dimensions: list[dict[str, Any]]) -> dict[str, Any]:
    fallback = fallback_questions(child_name, dimensions)
    valid = {item.get("key"):item for item in dimensions}
    real_briefs = {(item.get("key"),brief.get("evidence_ref")):(brief.get("module"),brief.get("text")) for item in dimensions for brief in item.get("evidence_brief", [])}
    globals_out = []
    for index, category in enumerate(("家庭陪伴","期待","在意")):
        item = candidate.get("global_questions", [])[index] if isinstance(candidate.get("global_questions"), list) and len(candidate["global_questions"]) > index else fallback["global_questions"][index]
        globals_out.append({"id":f"g{index+1}","category":category,"lead":str(item.get("lead", ""))[:8],"question":str(item.get("question", ""))[:30],"options":[str(v)[:8] for v in item.get("options", [])[:4]] or fallback["global_questions"][index]["options"],"allow_text":True,"placeholder":str(item.get("placeholder", ""))[:20]})
    dimension_out = []
    for index, item in enumerate(candidate.get("dimension_questions", [])[:2] if isinstance(candidate.get("dimension_questions"), list) else []):
        key, ref = item.get("key"), str(item.get("evidence_ref", ""))
        source = valid.get(key)
        matched = real_briefs.get((key, ref))
        if not source or not matched:
            continue
        module, text = matched
        dimension_out.append({"id":f"d{index+1}","key":key,"evidence_ref":ref,"module":module,"evidence_brief":text,"lead":str(item.get("lead", ""))[:8],"question":str(item.get("question", ""))[:30],"options":[str(v)[:8] for v in item.get("options", [])[:4]],"allow_text":True,"placeholder":str(item.get("placeholder", ""))[:20]})
    return {"question_version":QUESTION_VERSION,"lead_note":str(candidate.get("lead_note") or fallback["lead_note"])[:40],"global_questions":globals_out,"dimension_questions":dimension_out or fallback["dimension_questions"]}


def normalize_suggestions(candidate: dict[str, Any], child_name: str) -> dict[str, Any]:
    consistency = candidate.get("consistency") if isinstance(candidate.get("consistency"), dict) else {}
    conclusion = consistency.get("conclusion") if consistency.get("conclusion") in {"一致","仅平台显现","仅家庭显现","证据不足"} else "证据不足"
    clean = lambda key, low, high: [str(item).strip()[:60] for item in candidate.get(key, []) if str(item).strip()][:high] if isinstance(candidate.get(key), list) else []
    family = clean("family_suggestions", 4, 6)
    teacher = clean("teacher_suggestions", 3, 5)
    return {"consistency":{"conclusion":conclusion,"text":str(consistency.get("text", "")).strip()},"family_suggestions":family,"teacher_suggestions":teacher,"transition_note":str(candidate.get("transition_note") or f"带着您的回答，星章为{child_name}写好了新的建议")[:30]}
