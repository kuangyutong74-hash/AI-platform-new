"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ExplorerIcon from "./ExplorerIcon";
import useExplorerCollection from "../hooks/useExplorerCollection";
import type { ExplorerGrowthOverview, ExplorerItem, ExplorerModule, ExplorerSessionMoment } from "../lib/explorer-types";

type Account = { display_name: string; age: number; created_at?: string; avatar_id?: string };
type NavigationView = "planet" | "works" | "timeline" | "report";

function formatDate(value: string, withYear = true) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf()) || date.valueOf() === 0)
    return "最近一次探索";
  return new Intl.DateTimeFormat("zh-CN", {
    year: withYear ? "numeric" : undefined,
    month: "long",
    day: "numeric",
  }).format(date);
}

function formatDuration(seconds: number) {
  if (!seconds) return "尚未记录时长";
  const minutes = Math.max(1, Math.round(seconds / 60));
  if (minutes < 60) return `${minutes} 分钟`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} 小时 ${rest} 分钟` : `${hours} 小时`;
}

function formatShortDate(value: string) {
  const date = new Date(value);
  if (!value || Number.isNaN(date.valueOf())) return "";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
  }).format(date);
}

const reviewCopy = {
  registration: {
    observations: ["注册起点从这一天开始，之后每一次完整探索都会成为一枚可回看的脚印。"],
    question: "还记得第一次来到探索星球时，最想去哪里看看吗？",
    next: "选一座还没点亮的大陆，完成第一次探索。",
  },
  story: {
    observations: ["愿意沿着一个想法继续补充，让故事慢慢完整起来。", "在创作中会作出自己的选择，而不只是接受现成答案。"],
    question: "哪一个情节最像你的想法？如果再写一次，你最想改哪里？",
    next: "下次换一个角色或结局，留意自己会不会用新的讲法。",
  },
  deep_sea: {
    observations: ["会把大任务拆成配对、布局和协商等不同问题。", "看到结果不理想时，愿意回头检查并调整方案。"],
    question: "哪一次调整最有用？你是怎么发现原来的办法需要改变的？",
    next: "下次先说出计划再动手，完成后对照计划看看哪里发生了变化。",
  },
  career: {
    observations: ["能够跟随职业情境完成连续任务，并在关键节点作出选择。", "体验不同角色时，开始留意自己更投入的任务类型。"],
    question: "哪个任务让你最投入？是因为它有挑战，还是因为能帮助别人？",
    next: "换一种职业再体验一次，比较自己在哪类任务里更愿意坚持。",
  },
  chat: {
    observations: ["愿意从生活里的小事出发，把感受和原因慢慢说清楚。", "在被追问时能够继续补充，让表达变得更具体。"],
    question: "那次对话里，你最希望别人听懂的是哪一句？现在有没有新的想法？",
    next: "下次试着多说一个‘因为’，看看能不能把想法讲得更完整。",
  },
} as const;

function speak(text: string) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const voice = new SpeechSynthesisUtterance(text);
  voice.lang = "zh-CN";
  voice.rate = 0.82;
  voice.pitch = 1.06;
  window.speechSynthesis.speak(voice);
}

function TrailLine({ avatarUrl }: { avatarUrl: string }) {
  const shellRef = useRef<HTMLDivElement>(null);
  const guideRef = useRef<SVGPathElement>(null);
  const progressGlowRef = useRef<SVGPathElement>(null);
  const progressRef = useRef<SVGPathElement>(null);
  const travelerRef = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    let frame = 0;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const shell = shellRef.current,
          path = guideRef.current,
          traveler = travelerRef.current;
        if (!shell || !path || !traveler) return;
        const rect = shell.getBoundingClientRect();
        const travel = Math.max(rect.height - window.innerHeight * 0.55, 1);
        const progress = Math.min(
          1,
          Math.max(0, (window.innerHeight * 0.34 - rect.top) / travel),
        );
        const visibleProgress = Math.min(0.985, Math.max(0.012, progress));
        const pathLength = path.getTotalLength();
        const distance = pathLength * visibleProgress;
        const point = path.getPointAtLength(distance);
        const before = path.getPointAtLength(Math.max(0, distance - 2));
        const after = path.getPointAtLength(Math.min(pathLength, distance + 2));
        const angle =
          (Math.atan2(after.y - before.y, after.x - before.x) * 180) / Math.PI;
        traveler.style.left = `${point.x / 8}%`;
        traveler.style.top = `${point.y / 28}%`;
        traveler.style.setProperty("--trail-angle", `${angle}deg`);
        const dashOffset = String(1000 * (1 - progress));
        progressGlowRef.current?.style.setProperty(
          "stroke-dashoffset",
          dashOffset,
        );
        progressRef.current?.style.setProperty("stroke-dashoffset", dashOffset);
      });
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);
  const trailPath =
    "M401 0C680 220 669 486 390 654S121 1055 413 1244s284 448-7 620-276 491 7 936";
  return (
    <div className="growth-trail-line" ref={shellRef} aria-hidden="true">
      <svg viewBox="0 0 800 2800" preserveAspectRatio="none">
        <defs>
          <filter
            id="growth-trail-blur"
            x="-30%"
            y="-5%"
            width="160%"
            height="110%"
          >
            <feGaussianBlur stdDeviation="13" />
          </filter>
          <filter
            id="growth-soft-glow"
            x="-50%"
            y="-20%"
            width="200%"
            height="140%"
          >
            <feGaussianBlur stdDeviation="9" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <linearGradient id="growth-trail-paper" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#d8a86d" stopOpacity=".2" />
            <stop offset=".18" stopColor="#f4dfaa" stopOpacity=".3" />
            <stop offset=".52" stopColor="#fff5cb" stopOpacity=".22" />
            <stop offset=".82" stopColor="#e7c98e" stopOpacity=".3" />
            <stop offset="1" stopColor="#bd815d" stopOpacity=".18" />
          </linearGradient>
          <linearGradient id="growth-trail-gold" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fff9d8" />
            <stop offset=".55" stopColor="#f7d879" />
            <stop offset="1" stopColor="#eeb458" />
          </linearGradient>
        </defs>
        <path className="trail-shadow" d={trailPath} />
        <path className="trail-paper-edge" d={trailPath} />
        <path className="trail-paper-fill" d={trailPath} />
        <path className="trail-pencil-line" d={trailPath} />
        <path className="trail-stitches" d={trailPath} />
        <path ref={guideRef} className="trail-guide" d={trailPath} />
        <path
          ref={progressGlowRef}
          className="trail-progress-glow"
          d={trailPath}
          pathLength="1000"
        />
        <path
          ref={progressRef}
          className="trail-progress"
          d={trailPath}
          pathLength="1000"
        />
      </svg>
      <span ref={travelerRef} className="trail-traveler trail-child-traveler">
        <i className="trail-comet-tail" />
        <span className="trail-avatar-ring"><img src={avatarUrl} alt="" /></span>
        <b />
        <em />
      </span>
    </div>
  );
}

const growthModuleNames: Record<Exclude<ExplorerModule, "registration">, string> = {
  story: "想象之洲",
  deep_sea: "创造之洲",
  career: "未来之洲",
  chat: "倾听之洲",
};

const growthFollowups: Record<Exclude<ExplorerModule, "registration">, string> = {
  story: "可以问问：故事里哪一处是你最想保留的？如果继续写，会怎么发展？",
  deep_sea: "可以问问：哪一步需要重新调整？你当时先检查了什么？",
  career: "可以问问：哪个工作环节最难？你后来怎样完成它？",
  chat: "可以接着问：你为什么这样想？有没有一件具体的小事让你想到它？",
};

function selectOtherSessions(sessions: ExplorerSessionMoment[], latest: ExplorerSessionMoment) {
  const selected: ExplorerSessionMoment[] = [];
  const modules = new Set([latest.module]);
  for (const session of sessions) {
    if (session.id === latest.id || modules.has(session.module)) continue;
    selected.push(session);
    modules.add(session.module);
    if (selected.length === 3) return selected;
  }
  for (const session of sessions) {
    if (session.id !== latest.id && !selected.some(item => item.id === session.id)) selected.push(session);
    if (selected.length === 3) break;
  }
  return selected;
}

function GrowthOverviewPanel({
  overview,
  adult,
  isDemo,
}: {
  overview: ExplorerGrowthOverview;
  adult: boolean;
  isDemo: boolean;
}) {
  const person = adult ? "孩子" : "你";
  const latest = overview.sessions[0] ?? overview.todaySessions[0];
  const otherSessions = latest ? selectOtherSessions(overview.sessions, latest) : [];
  const isToday = latest && overview.todaySessions.some(session => session.id === latest.id);
  return (
    <section className="growth-overview" aria-labelledby="growth-overview-title">
      <header>
        <div>
          <p>{isDemo ? "示例探索记录" : "成长足迹 · 过程记录"}</p>
          <h2 id="growth-overview-title">每一次探索，都留下了什么</h2>
        </div>
        <span>{overview.todayCompletedCount ? `今天新增 ${overview.todayCompletedCount} 次完成` : "今天暂无新完成"}</span>
      </header>
      <div className="growth-overview-stats" aria-label="探索记录概况">
        <span><b>{overview.totalCompletedCount}</b>次完成的探索</span>
        <span><b>{overview.activeDays}</b>个有记录的日子</span>
        <span><b>{overview.exploredModuleCount}</b>类探索活动</span>
      </div>
      {latest ? (
        <>
          <article className="growth-featured-record">
            <div className="growth-record-kicker">{isToday ? "今天的完成" : "最近一次完成"} · {formatShortDate(latest.occurredAt)}</div>
            <div className="growth-featured-main">
              <div>
                <span className="growth-record-module">{growthModuleNames[latest.module!]}</span>
                <h3>{latest.caption}</h3>
                {latest.detail ? <p>{latest.detail}</p> : null}
              </div>
              <aside><b>下次可以这样聊</b><span>{growthFollowups[latest.module!]}</span></aside>
            </div>
          </article>
          {otherSessions.length ? (
            <div className="growth-history-section">
              <div className="growth-history-heading"><h3>继续回看</h3><span>先看不同活动中的最近记录，完整足迹在下方</span></div>
              <ul className="growth-history-grid">
                {otherSessions.map(session => (
                  <li key={session.id}>
                    <div className="growth-history-meta"><strong>{growthModuleNames[session.module!]}</strong><time>{formatShortDate(session.occurredAt)}</time></div>
                    <h4>{session.caption}</h4>
                    {session.detail ? <p>{session.detail}</p> : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : (
        <div className="growth-overview-empty"><ExplorerIcon name="compass" /><p>还没有完成的探索。完成一次活动后，这里会记录当时做了什么。</p></div>
      )}
      <p className="growth-evidence-note">
        这里记录的是{person}在平台任务中做过的事。可以结合孩子自述和日常观察继续了解，单次完成不代表固定能力。
      </p>
    </section>
  );
}

function TrailDialog({
  item,
  isDemo,
  adult,
  onClose,
  onNavigate,
}: {
  item: ExplorerItem;
  isDemo: boolean;
  adult: boolean;
  onClose: () => void;
  onNavigate: (view: NavigationView) => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
    document.body.classList.add("dialog-open");
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab") return;
      const items = [
        ...(dialogRef.current?.querySelectorAll<HTMLElement>(
          'button,a[href],[tabindex]:not([tabindex="-1"])',
        ) ?? []),
      ].filter((node) => !node.hasAttribute("disabled"));
      if (!items.length) return;
      const first = items[0],
        last = items.at(-1)!;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.classList.remove("dialog-open");
    };
  }, [onClose]);
  const copy = reviewCopy[item.module];
  const observations = item.observations.length ? item.observations : [...copy.observations];
  const spokenReview = [
    item.title,
    ...observations,
    `可以一起聊聊：${copy.question}`,
    `下一站建议：${copy.next}`,
  ].join("。");
  return (
    <div
      className="trail-dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <section
        className="trail-memory-book trail-evidence-sheet"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="trail-dialog-title"
      >
        <button
          ref={closeRef}
          className="trail-dialog-close"
          onClick={onClose}
          aria-label="合上完成历程手账"
        >
          <ExplorerIcon name="close" />
        </button>
        <div className="memory-picture">
          <p>{item.island} · 成长回顾</p>
          <img src={item.milestoneImage} alt="" />
          {item.kind === "registration" ? (
            <span>{item.status}</span>
          ) : (
            <div className="memory-snapshot-stats" aria-label="这一站的探索概况">
              <span><b>{item.usageCount}</b>次完成</span>
              <span><b>{formatDuration(item.durationSeconds)}</b>累计投入</span>
              <span><b>{item.evidenceCount}</b>条过程记录</span>
            </div>
          )}
          <p className="memory-boundary">
            这里回顾的是探索过程与变化；作品内容会在作品展柜里单独收藏。
          </p>
        </div>
        <div className="memory-seam" aria-hidden="true" />
        <article>
          <p className="memory-date">
            {isDemo ? "示例完成历程" : "我的真实完成历程"} ·{" "}
            {formatDate(item.occurredAt)}
          </p>
          <h2 id="trail-dialog-title">{item.title}</h2>
          {item.kind !== "registration" && item.firstUsedAt && (
            <div className="memory-period" aria-label="完成时间范围">
              <span><b>第一次完成</b>{formatDate(item.firstUsedAt)}</span>
              <span><b>最近一次完成</b>{formatDate(item.lastUsedAt || item.occurredAt)}</span>
            </div>
          )}
          <p className="growth-role-note">这里只回顾孩子怎样完成、怎样调整；作品正文与完整成果留在作品展柜。</p>
          <p className="memory-heading">发生了什么</p>
          <p className="memory-note">{item.detail}</p>
          <section className="memory-section memory-observations">
            <p className="memory-heading">孩子怎样做的</p>
            <ul>
              {observations.map((observation) => <li key={observation}>{observation}</li>)}
            </ul>
          </section>
          {item.recentSessions.length > 0 && (
            <section className="memory-section memory-footprints">
              <p className="memory-heading">前后变化的依据</p>
              <ol>
                {item.recentSessions.map((session) => (
                  <li key={session.id}>
                    <time>{formatDate(session.occurredAt)}</time>
                    <span>{session.caption}</span>
                    {session.durationSeconds > 0 && <small>{formatDuration(session.durationSeconds)}</small>}
                  </li>
                ))}
              </ol>
            </section>
          )}
          <div className="memory-family-card">
            <span>{adult ? "今晚可以这样聊" : "可以和家人聊聊"}</span>
            <p>{copy.question}</p>
          </div>
          <div className="memory-next-step">
            <ExplorerIcon name="spark" size={16} />
            <p><b>下一站建议</b>{copy.next}</p>
          </div>
          <p className="evidence-caution">这里只记录发生过的过程，不根据点击、拖动或操作次数判断能力高低。</p>
          <button
            className="memory-listen"
            onClick={() => speak(spokenReview)}
          >
            <ExplorerIcon name="headphones" />
            听完整回顾
          </button>
          <div className="memory-actions">
            <button className="gold-button" onClick={onClose}>
              <ExplorerIcon name="spark" />
              收好这页回顾
            </button>
            {item.artifactCount > 0 && (
              <button className="memory-work-link" onClick={() => onNavigate("works")}>
                <ExplorerIcon name="book" />
                查看关联作品（{item.artifactCount}）
              </button>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}

export default function GrowthTrailPage({
  account,
  onNavigate,
  perspective = "student",
}: {
  account: Account;
  onNavigate: (view: NavigationView) => void;
  perspective?: "student" | "adult";
}) {
  const { data, loading, error, retry } = useExplorerCollection(account);
  const [selected, setSelected] = useState<ExplorerItem | null>(null);
  const [timeFilter, setTimeFilter] = useState<"all" | "month" | "quarter">("all");
  const [moduleFilter, setModuleFilter] = useState("all");
  const lastTrigger = useRef<HTMLButtonElement | null>(null);
  const closeDialog = useCallback(() => {
    setSelected(null);
    window.setTimeout(() => lastTrigger.current?.focus(), 50);
  }, []);
  if (loading || !data)
    return (
      <section className="personal-loading" aria-live="polite">
        <span className="loading-star">
          <ExplorerIcon name="spark" size={38} />
        </span>
        <h1>正在整理你的完成历程…</h1>
        <p>从注册那天开始，每一次完成都在赶来和你见面。</p>
      </section>
    );
  const avatarUrl = `http://localhost:3000/assets/avatars/student/${account.avatar_id || "student-1"}.png`;
  const newestTime = Math.max(...data.milestones.map((item) => new Date(item.occurredAt).valueOf() || 0), Date.now());
  const dayLimit = timeFilter === "month" ? 31 : timeFilter === "quarter" ? 93 : Infinity;
  const milestones = data.milestones.filter((item) => {
    const itemTime = new Date(item.occurredAt).valueOf() || newestTime;
    return (newestTime - itemTime) / 86400000 <= dayLimit && (moduleFilter === "all" || item.module === moduleFilter);
  }).slice(0, 8);
  const adult = perspective === "adult";
  const allUnlocked = data.milestones.filter(
    (item) => item.module !== "registration" && item.unlocked,
  );
  const usedModuleCount = new Set(allUnlocked.map((item) => item.module)).size;
  const totalExplorations = allUnlocked.reduce((sum, item) => sum + Math.max(0, item.usageCount || 0), 0);
  const open = (item: ExplorerItem, trigger: HTMLButtonElement) => {
    if (!item.unlocked) return;
    lastTrigger.current = trigger;
    setSelected(item);
  };
  return (
    <main className={`growth-view ${adult ? "growth-parent-view" : ""}`}>
      <div className="growth-cloud growth-cloud-one" aria-hidden="true" />
      <div className="growth-cloud growth-cloud-two" aria-hidden="true" />
      <header className="growth-hero growth-parent-hero" aria-labelledby="growth-title">
        <button className="growth-back" onClick={() => onNavigate("planet")}>
          <ExplorerIcon name="compass" />
          {adult ? "回天赋报告" : "回探索星球"}
        </button>
        <div className="growth-avatar">
          <img src={avatarUrl} alt={`${data.account.displayName}的头像`} />
        </div>
        <div className="growth-hero-copy">
          <div>
            <h1 id="growth-title">
              {data.account.displayName}的成长足迹
            </h1>
            <ExplorerIcon name="spark" size={28} />
          </div>
          <p className="growth-promise">从 {formatDate(data.account.createdAt)} 开始记录</p>
          <div className="growth-facts" aria-label="成长记录概览">
            <span><strong>{totalExplorations}</strong> 次完整探索</span>
            <span><strong>{usedModuleCount}</strong> 类活动</span>
            <span><strong>{data.growthOverview.activeDays}</strong> 个探索日</span>
          </div>
          <p className="growth-source">
            {data.timelineIsDemo ? "示例记录 · " : ""}看见孩子如何尝试、调整，并在一次次探索中发生变化。
          </p>
        </div>
        <span className="growth-tape tape-one" aria-hidden="true" />
        <span className="growth-tape tape-two" aria-hidden="true" />
      </header>
      <div className={`growth-notice ${error ? "is-error" : ""}`} role="status">
        <ExplorerIcon name="spark" />
        <span>{data.timelineNotice}</span>
        {error && <button onClick={retry}>再试一次</button>}
      </div>
      <GrowthOverviewPanel
        overview={data.growthOverview}
        adult={adult}
        isDemo={data.timelineIsDemo}
      />
      <nav className="growth-filters" aria-label="筛选成长记录">
        <div>
          <button className={timeFilter === "all" ? "is-active" : ""} onClick={() => setTimeFilter("all")}>全部时间</button>
          <button className={timeFilter === "month" ? "is-active" : ""} onClick={() => setTimeFilter("month")}>本月</button>
          <button className={timeFilter === "quarter" ? "is-active" : ""} onClick={() => setTimeFilter("quarter")}>最近三个月</button>
        </div>
        <label>活动类型
          <select value={moduleFilter} onChange={(event) => setModuleFilter(event.target.value)}>
            <option value="all">全部活动</option><option value="story">故事共创</option><option value="chat">聊天观察</option><option value="deep_sea">深海基地重建</option><option value="career">职业模拟</option><option value="registration">星光起点</option>
          </select>
        </label>
      </nav>
      <section
        className="growth-trail"
        aria-label={`${data.account.displayName}的成长星路`}
      >
        <div className="growth-intro">
          <ExplorerIcon name="spark" />
          <p>
            第一站，是{adult ? "孩子" : "你"}来到探索星球的那一天。往后每一站只记录发生了什么、怎样完成、有什么变化，以及下一步可以怎样尝试。
          </p>
        </div>
        <TrailLine avatarUrl={avatarUrl} />
        <div className="milestone-list">
          {milestones.map((item, index) => (
            <article
              key={item.id}
              className={`growth-milestone evidence-milestone ${index % 2 ? "side-right" : "side-left"} tone-${item.tone} ${item.unlocked ? "is-unlocked" : "is-locked"}`}
            >
              <span className="milestone-node" aria-hidden="true"><ExplorerIcon name="spark" size={20} /></span>
              <div className="milestone-scene" aria-label={`${item.island}阶段场景`}>
                <span className="milestone-scene-glow" aria-hidden="true" />
                <img
                  src={item.milestoneImage}
                  alt={`${item.island}阶段插画`}
                  loading={index < 2 ? "eager" : "lazy"}
                />
                <small>阶段场景</small>
              </div>
              <div className="milestone-copy">
                <div className="milestone-heading"><p className="milestone-island">{item.island}</p><time>{formatDate(item.occurredAt, false)}</time></div>
                <h2>{item.title}</h2>
                <p className="milestone-observation">{item.detail || item.summary}</p>
                {item.kind !== "registration" && <p className="milestone-usage milestone-context">
                  <span>{item.metricLabel}</span>
                  <strong>{item.metricValue}</strong>
                </p>}
                <div className="milestone-actions">
                  <button className="milestone-open" onClick={(event) => open(item, event.currentTarget)}>查看过程回顾 <ExplorerIcon name="arrow" /></button>
                  {data.works.find((work) => work.module === item.module) && <button className="milestone-work-link" onClick={() => onNavigate("works")}><ExplorerIcon name="book" size={16} />关联作品：《{data.works.find((work) => work.module === item.module)?.title}》</button>}
                </div>
              </div>
            </article>
          ))}
        </div>
        <aside className="growth-reflection" aria-labelledby="reflection-title">
          <span className="reflection-star"><ExplorerIcon name="spark" size={28} /></span>
          <div><p>阶段回望</p><h2 id="reflection-title">把重复出现的过程线索放在一起看</h2><p>{allUnlocked.length >= 2 ? `本阶段已有 ${allUnlocked.length} 类活动留下记录。可以继续观察“先检查、再修改”等过程是否会在不同任务中稳定复现。` : "目前记录还不多，先保留这次具体行为，等更多独立活动出现后再判断是否形成稳定线索。"}</p></div>
          <button className="plain-button" onClick={() => onNavigate("report")}><ExplorerIcon name="book" />查看阶段性报告</button>
        </aside>
      </section>
      <footer className="starlight-camp growth-continuation">
        <div className="camp-stars" aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
        </div>
        <img
          src="/assets/collections/growth/starlight-camp-720.webp"
          alt=""
          loading="lazy"
        />
        <div>
          <p className="growth-eyebrow">TO BE CONTINUED</p>
          <h2>记录仍在继续</h2>
          <p>
            这里从注册日开始，整理了 {usedModuleCount} 座已点亮大陆的完成节奏和过程变化。
            新的探索会继续补进这本成长手账。
          </p>
          <div>
            <button className="gold-button" onClick={() => onNavigate("report")}>
              <ExplorerIcon name="book" />
              查看阶段性报告
            </button>
            <button
              className="plain-button"
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            >
              <ExplorerIcon name="compass" />
              筛选时间
            </button>
            <button className="plain-button" onClick={() => window.print()}>导出阶段回顾</button>
          </div>
        </div>
      </footer>
      {selected && (
        <TrailDialog
          item={selected}
          isDemo={data.timelineIsDemo}
          adult={adult}
          onClose={closeDialog}
          onNavigate={onNavigate}
        />
      )}
    </main>
  );
}
