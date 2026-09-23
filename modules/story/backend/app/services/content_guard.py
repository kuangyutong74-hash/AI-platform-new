"""Privacy guard for the story co-creation module.

Only concrete personal identifiers are blocked by deterministic rules. Story
language is intentionally passed to the director model so it can judge tone and
context instead of rejecting harmless words such as "打", "炸" or "恐怖".
"""

import re
from dataclasses import dataclass

# Concrete, attributable details only. A child's age or province/city is not
# considered identifying enough to block. Generic story references such as
# "学校里的故事" and fictional passwords are also allowed.
PRIVACY_PATTERNS = (
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    re.compile(r"(?:手机(?:号)?|电话(?:号码)?|联系方式)(?:是|为|：|:)?\s*\d{7,11}"),
    re.compile(r"(?:微信(?:号)?|QQ(?:号)?|邮箱)(?:是|为|：|:)\s*[A-Za-z0-9_.@+-]{4,}", re.I),
    re.compile(r"(?:我的真实姓名|我的姓名|真实姓名|姓名)(?:是|为|叫|：|:)\s*[\u4e00-\u9fff·]{2,8}"),
    re.compile(r"(?:我(?:在|就读于)|我的学校(?:是|叫|为)|学校(?:是|叫|为))"
               r"[^，。！？\n]{2,30}(?:学校|小学|中学|高中|大学)"),
    re.compile(r"(?:我是|我在)[一二三四五六七八九十\d]{1,3}年级"
               r"[\u4e00-\u9fff\d]{0,6}班"),
    re.compile(r"(?:我家住(?:在)?|我住在|家庭住址(?:是|为)?|(?:我的)?地址(?:是|为)?)"
               r"[^，。！？\n]{0,50}(?:小区|街道|路|街|巷|弄|村|社区|公寓|"
               r"\d+号|\d+栋|\d+幢|\d+单元|\d+室|\d+楼)"),
    re.compile(r"(?:我的|账号|账户|登录|支付|银行卡)[^，。！？\n]{0,8}"
               r"(?:密码|口令)(?:是|为|：|:)\s*[^，。！？\s]{3,}"),
    re.compile(r"验证码(?:是|为|：|:)\s*\d{4,8}"),
)

INPUT_BLOCK_MESSAGE = (
    "这句话里可能包含过于具体的个人信息。请不要填写真实住址、学校、班级、"
    "电话、姓名或账号密码，改成虚构信息后再继续吧。"
)
EMPTY_AFTER_CLEAN_MESSAGE = "本次内容包含过于具体的个人信息，请修改后重新创作。"
PARENT_REMINDER = (
    "为了保护个人隐私，这一轮先暂停。请去掉真实住址、学校、班级、电话、"
    "姓名或账号密码，改成虚构信息后再继续吧。"
)
PRIVACY_REMINDER = "不要在故事里填写个人真实信息，保护自己隐私。"


# ── Engagement signals for child interaction exceptions ──

STUCK_KEYWORDS = {"不知道", "不会", "不知道写什么", "想不到", "没想好", "随便", "都行", "嗯", "哦", "好", "行", "可以", "还行"}
OFF_TOPIC_KEYWORDS = {"游戏", "手机", "零食", "作业", "考试", "分数", "老师批评", "同学欺负", "动画片", "玩具", "奥特曼", "王者荣耀", "吃鸡"}
WANT_TO_STOP_KEYWORDS = {"不想写了", "不想玩了", "好累", "累了", "没意思", "不好玩", "写不动", "不玩了", "结束吧", "算了吧", "不要了"}

@dataclass
class EngagementResult:
    issue_type: str   # "stuck" | "off_topic" | "want_to_stop" | "OK"
    prompt_hint: str  # Extra instruction to inject into the system prompt


def check_engagement(text: str) -> EngagementResult:
    """Detect if the child is stuck, off-topic, or wants to stop.

    Returns EngagementResult with hints for the story director.
    """
    if not text or not text.strip():
        return EngagementResult(issue_type="OK", prompt_hint="")

    normalized = text.strip()

    # 1. Want to stop?
    for kw in WANT_TO_STOP_KEYWORDS:
        if kw in normalized:
            return EngagementResult(
                issue_type="want_to_stop",
                prompt_hint="孩子表达了不想继续的情绪。请用温暖的方式回应：先共情,然后给故事一个简短而温暖的结局,使用ending事件收尾。不要追问。",
            )

    # 2. Stuck / can't think?
    word_count = len(normalized.replace(" ", ""))
    if word_count <= 3:
        return EngagementResult(
            issue_type="stuck",
            prompt_hint='孩子似乎卡住了，回答很短。请给出1-2个具体的续写方向供TA选择，鼓励TA大胆想。不要只说再想想。',
        )
    for kw in STUCK_KEYWORDS:
        if kw == normalized or (kw in normalized and word_count <= 5):
            return EngagementResult(
                issue_type="stuck",
                prompt_hint="孩子的回答很短或表示不知道。请给出2个具体有趣的续写建议让TA选，降低创作压力。先肯定TA之前的贡献再引导。",
            )

    # 3. Off-topic?
    for kw in OFF_TOPIC_KEYWORDS:
        if kw in normalized:
            return EngagementResult(
                issue_type="off_topic",
                prompt_hint='孩子聊到了和故事无关的话题。请用轻松幽默的方式把注意力拉回故事，在下一段叙事中自然地衔接回故事主线。',
            )

    return EngagementResult(issue_type="OK", prompt_hint="")


@dataclass
class SafetyResult:
    is_flagged: bool
    level: str          # "heavy" | "moderate" | "mild" | "safe"
    triggered_word: str
    kind_message: str   # Child-friendly reminder text


@dataclass
class InputGuardResult:
    blocked: bool
    sanitized_text: str
    has_privacy: bool
    category: str
    message: str


@dataclass
class CleanTextResult:
    cleaned_text: str
    removed_count: int
    has_privacy: bool
    has_prohibited: bool


def redact_privacy(text: str) -> tuple[str, bool]:
    sanitized = text
    found = False
    for pattern in PRIVACY_PATTERNS:
        sanitized, count = pattern.subn("[已隐藏的个人信息]", sanitized)
        found = found or count > 0
    return sanitized, found


def contains_prohibited_content(text: str) -> bool:
    """Compatibility helper: only private identifying details are prohibited."""
    return redact_privacy(text)[1]


def guard_child_input(text: str) -> InputGuardResult:
    """Block concrete private details; leave story language to the LLM."""
    sanitized, has_privacy = redact_privacy(text.strip())
    if has_privacy:
        return InputGuardResult(
            blocked=True,
            sanitized_text="",
            has_privacy=True,
            category="privacy",
            message=INPUT_BLOCK_MESSAGE,
        )
    return InputGuardResult(
        blocked=False,
        sanitized_text=sanitized,
        has_privacy=False,
        category="safe",
        message="",
    )


def clean_submitted_text(text: str) -> CleanTextResult:
    """Delete sentences containing concrete private details before storage."""
    sentences = [
        part.strip()
        for part in re.split(r"(?<=[。！？!?；;])|\n+", text)
        if part.strip()
    ]
    safe_sentences = []
    removed_count = 0
    has_privacy = False
    has_prohibited = False
    for sentence in sentences:
        _, sentence_has_privacy = redact_privacy(sentence)
        if sentence_has_privacy:
            removed_count += 1
            has_privacy = has_privacy or sentence_has_privacy
            continue
        safe_sentences.append(sentence)
    return CleanTextResult(
        cleaned_text="".join(safe_sentences).strip(),
        removed_count=removed_count,
        has_privacy=has_privacy,
        has_prohibited=has_prohibited,
    )


def sanitize_agent_output(text: str) -> str:
    """Trust the director's contextual language judgment; preserve its prose."""
    return text.strip()


def check_content(text: str) -> SafetyResult:
    """Legacy API that now reports only concrete privacy exposure."""
    has_privacy = redact_privacy(text)[1] if text and text.strip() else False
    return SafetyResult(
        is_flagged=has_privacy,
        level="moderate" if has_privacy else "safe",
        triggered_word="personal_information" if has_privacy else "",
        kind_message=INPUT_BLOCK_MESSAGE if has_privacy else "",
    )
