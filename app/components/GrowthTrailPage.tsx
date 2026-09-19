"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ExplorerIcon from "./ExplorerIcon";
import useExplorerCollection from "../hooks/useExplorerCollection";
import type { ExplorerGrowthOverview, ExplorerItem, ExplorerModule } from "../lib/explorer-types";

type Account = { display_name: string; age: number; created_at?: string };
type NavigationView = "planet" | "works" | "timeline" | "report";

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf()) || date.valueOf() === 0)
    return "最近一次探索";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
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

const reviewCopy = {
  registration: {
    observations: ["从这一天开始，之后每一次完整探索都会成为一枚可回看的脚印。"],
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

function TrailLine() {
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
      <span ref={travelerRef} className="trail-traveler">
        <i className="trail-comet-tail" />
        <svg viewBox="0 0 64 64">
          <defs>
            <radialGradient id="growth-traveler-gold" cx="42%" cy="34%">
              <stop offset="0" stopColor="#fffef0" />
              <stop offset=".36" stopColor="#fff0a0" />
              <stop offset=".76" stopColor="#f6c84c" />
              <stop offset="1" stopColor="#d8952f" />
            </radialGradient>
          </defs>
          <path
            className="traveler-star"
            d="M32 3 39.6 19.1 57 21.3 44.2 33.5 47.5 50.7 32 42.2 16.5 50.7 19.8 33.5 7 21.3 24.4 19.1Z"
          />
          <path className="traveler-shine" d="M25 18c3.7-5 8.5-6.7 13.5-4" />
        </svg>
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

function GrowthOverviewPanel({
  overview,
  adult,
  isDemo,
}: {
  overview: ExplorerGrowthOverview;
  adult: boolean;
  isDemo: boolean;
}) {
  const todayLabel = new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date());
  const person = adult ? "孩子" : "你";
  return (
    <section className="growth-overview" aria-labelledby="growth-overview-title">
      <header>
        <div>
          <p>{isDemo ? "示例观察面板" : "真实探索证据"}</p>
          <h2 id="growth-overview-title">今天与长期以来</h2>
        </div>
        <span>把一次表现和反复出现的线索分开看</span>
      </header>
      <div className="growth-overview-grid">
        <article className="growth-today-card">
          <div className="growth-card-heading">
            <span className="growth-card-icon"><ExplorerIcon name="spark" /></span>
            <div><small>{todayLabel}</small><h3>今天的足迹</h3></div>
          </div>
          {overview.todayCompletedCount > 0 ? (
            <>
              <div className="growth-stat-row">
                <span><b>{overview.todayCompletedCount}</b><small>次完成</small></span>
                <span><b>{overview.todayModules.length}</b><small>座大陆</small></span>
                <span><b>{formatDuration(overview.todayDurationSeconds)}</b><small>今日投入</small></span>
              </div>
              <ol className="growth-today-list">
                {overview.todaySessions.slice(0, 3).map((session) => (
                  <li key={session.id}>
                    <i />
                    <span><b>{growthModuleNames[session.module!]}</b>{session.caption}</span>
                    {session.evidenceCount ? <small>{session.evidenceCount} 条过程记录</small> : null}
                  </li>
                ))}
              </ol>
            </>
          ) : (
            <div className="growth-overview-empty">
              <ExplorerIcon name="compass" />
              <p>今天还没有新的完成记录。下一次认真尝试，也会成为一枚新的脚印。</p>
            </div>
          )}
        </article>

        <article className="growth-long-card">
          <div className="growth-card-heading">
            <span className="growth-card-icon"><ExplorerIcon name="compass" /></span>
            <div><small>{overview.firstCompletedAt ? `从 ${formatDate(overview.firstCompletedAt)} 开始` : "从第一次探索开始"}</small><h3>长期以来的线索</h3></div>
          </div>
          <div className="growth-stat-row">
            <span><b>{overview.totalCompletedCount}</b><small>次完整探索</small></span>
            <span><b>{overview.activeDays}</b><small>个探索日</small></span>
            <span><b>{overview.exploredModuleCount}</b><small>类不同情境</small></span>
          </div>
          {overview.longTermSignals.length ? (
            <div className="growth-signal-list">
              {overview.longTermSignals.slice(0, 4).map((signal) => (
                <div key={signal.key} className="growth-signal">
                  <span><b>{signal.label}</b><em>{signal.status}</em></span>
                  <p>{signal.observation}</p>
                  <small>
                    来自 {signal.evidenceCount} 条证据
                    {signal.modules.length ? ` · ${signal.modules.map(module => growthModuleNames[module]).join("、")}` : ""}
                  </small>
                </div>
              ))}
            </div>
          ) : (
            <div className="growth-overview-empty compact">
              <p>再完成几次不同情境的探索，反复出现的做法会在这里慢慢连成线。</p>
            </div>
          )}
        </article>
      </div>
      <p className="growth-evidence-note">
        <ExplorerIcon name="spark" size={15} />
        这里呈现的是{person}在不同任务里的过程证据和变化，不是一次测验，也不是固定标签。
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
        className="trail-memory-book"
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
          <section className="memory-section memory-observations">
            <p className="memory-heading">从过程中看见</p>
            <ul>
              {observations.map((observation) => <li key={observation}>{observation}</li>)}
            </ul>
          </section>
          {item.recentSessions.length > 0 && (
            <section className="memory-section memory-footprints">
              <p className="memory-heading">最近的探索脚印</p>
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
  const [lockedId, setLockedId] = useState<string | null>(null);
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
  const milestones = data.milestones.slice(0, 8);
  const adult = perspective === "adult";
  const usedModuleCount = milestones.filter(
    (item) => item.module !== "registration" && item.unlocked,
  ).length;
  const open = (item: ExplorerItem, trigger: HTMLButtonElement) => {
    if (!item.unlocked) {
      setLockedId(item.id);
      window.setTimeout(
        () => setLockedId((current) => (current === item.id ? null : current)),
        5200,
      );
      return;
    }
    lastTrigger.current = trigger;
    setSelected(item);
  };
  return (
    <main className="growth-view">
      <div className="growth-cloud growth-cloud-one" aria-hidden="true" />
      <div className="growth-cloud growth-cloud-two" aria-hidden="true" />
      <header className="growth-hero" aria-labelledby="growth-title">
        <button className="growth-back" onClick={() => onNavigate("planet")}>
          <ExplorerIcon name="compass" />
          {adult ? "回天赋报告" : "回探索星球"}
        </button>
        <div className="growth-avatar" aria-hidden="true">
          <svg viewBox="0 0 120 120">
            <path
              d="M20 69c0-23 18-42 40-42s40 19 40 42c0 19-17 34-40 34S20 88 20 69Z"
              fill="#f2c9a0"
            />
            <path
              d="M29 55c4-28 26-39 49-29 9 4 15 13 17 25-14-7-23-16-27-26-7 14-20 24-39 30Z"
              fill="#394d77"
            />
            <path
              d="M24 43c8-20 24-30 43-30 16 0 29 7 36 21-23-8-49-5-79 9Z"
              fill="#6e9bc4"
            />
            <path
              d="M21 43c31-8 59-9 84-2"
              fill="none"
              stroke="#26385e"
              strokeWidth="5"
              strokeLinecap="round"
            />
            <circle cx="46" cy="66" r="3" fill="#27304b" />
            <circle cx="75" cy="66" r="3" fill="#27304b" />
            <path
              d="M51 82c7 5 14 5 21 0"
              fill="none"
              stroke="#b56d6a"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <path
              d="M15 95c12-8 26-12 43-12 20 0 37 5 48 15v22H15V95Z"
              fill="#e7a28e"
              opacity=".9"
            />
          </svg>
        </div>
        <div className="growth-hero-copy">
          <div>
            <h1 id="growth-title">
              {data.account.displayName}的成长足迹
            </h1>
            <ExplorerIcon name="spark" size={28} />
          </div>
          <p className="growth-promise">{adult ? "从第一天出发，看见孩子一步步走过的路。" : "从第一天出发，看见自己走过的路。"}</p>
          <p className="growth-summary">
            从注册起点出发，{adult ? "孩子" : "你"}已经点亮了 <strong>{usedModuleCount}</strong>{" "}
            座探索大陆。
          </p>
          <p className="growth-source">
            {data.timelineIsDemo
              ? "示例完成历程 · 真实记录会从你的注册日开始"
              : "账号注册与四个探索模块的真实完成小结"}
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
      <section
        className="growth-trail"
        aria-label={`${data.account.displayName}的成长星路`}
      >
        <div className="growth-intro">
          <ExplorerIcon name="spark" />
          <p>
            第一站，是{adult ? "孩子" : "你"}来到探索星球的那一天。往后每一站，都整理完成节奏、过程变化和下一次可以尝试的方向。
          </p>
        </div>
        <TrailLine />
        <div className="milestone-list">
          {milestones.map((item, index) => (
            <article
              key={item.id}
              className={`growth-milestone ${index % 2 ? "side-right" : "side-left"} tone-${item.tone} ${item.unlocked ? "is-unlocked" : "is-locked"}`}
            >
              <div className="milestone-visual-wrap">
                <button
                  className="milestone-visual"
                  onClick={(event) => open(item, event.currentTarget)}
                  aria-label={`${item.island}：${item.title}${item.unlocked ? "，打开完成小结" : "，查看点亮提示"}`}
                >
                  <span className="milestone-halo" />
                  <img
                    src={item.milestoneImage}
                    alt={`${item.island}水彩探索插画`}
                    loading={index === 0 ? "eager" : "lazy"}
                  />
                  <span className="milestone-number" aria-hidden="true">
                    {index + 1}
                  </span>
                </button>
              </div>
              <div className="milestone-copy">
                <p className="milestone-island">{item.island}</p>
                <h2>{item.title}</h2>
                <p className="milestone-date">
                  {item.unlocked
                    ? `${item.kind === "registration" ? "注册于" : "最近完成"} ${formatDate(item.occurredAt)}`
                    : "等待下一次出发"}
                </p>
                <p className="milestone-usage">
                  <span>{item.metricLabel}</span>
                  <strong>{item.metricValue}</strong>
                </p>
                <p className="milestone-label">
                  <ExplorerIcon name="spark" size={14} />
                  {item.status}
                </p>
                <button
                  className="milestone-open"
                  onClick={(event) => open(item, event.currentTarget)}
                >
                  {item.unlocked ? "打开这页完成小结" : "看看怎样点亮"}
                  <ExplorerIcon name="arrow" />
                </button>
              </div>
              {lockedId === item.id && (
                <div className="unlock-note" role="status">
                  <strong>这颗星还在云后面悄悄等你。</strong>
                  <span>第一次进入{item.island}并完成探索，就能把它点亮啦。</span>
                  <button onClick={() => onNavigate("planet")}>
                    现在去看看
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      </section>
      <footer className="starlight-camp">
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
          <h2>从第一颗星到今天，每一次完成都有自己的位置</h2>
          <p>
            这里从注册日开始，整理了 {usedModuleCount} 座已点亮大陆的完成节奏和过程变化。
            新的探索会继续补进这本成长手账。
          </p>
          <div>
            <button className="gold-button" onClick={() => onNavigate("works")}>
              <ExplorerIcon name="book" />
              看看高光作品
            </button>
            <button
              className="plain-button"
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            >
              <ExplorerIcon name="compass" />
              回到星路起点
            </button>
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
