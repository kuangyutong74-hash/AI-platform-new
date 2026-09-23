"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ExplorerIcon from "./ExplorerIcon";
import useExplorerCollection from "../hooks/useExplorerCollection";
import type { ExplorerItem } from "../lib/explorer-types";

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

function TrailDialog({
  item,
  isDemo,
  onClose,
  onNavigate,
}: {
  item: ExplorerItem;
  isDemo: boolean;
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
          <p>{item.island}</p>
          <img src={item.milestoneImage} alt="" />
          <span>{item.status}</span>
          {item.quote && (
            <blockquote>“{item.quote.replace(/[“”]/g, "")}”</blockquote>
          )}
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
          <p className="memory-heading">这次看见的具体过程</p>
          <p className="memory-note">{item.detail}</p>
          <p className="evidence-caution">这里只记录发生过的过程，不根据点击、拖动或操作次数判断能力高低。</p>
          <button
            className="memory-listen"
            onClick={() => speak(`${item.title}。${item.detail}`)}
          >
            <ExplorerIcon name="headphones" />
            听小纸条
          </button>
          <div className="memory-actions">
            <button className="gold-button" onClick={() => onNavigate("works")}>
              <ExplorerIcon name="book" />
              查看关联作品
            </button>
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
            <span><strong>{data.works.length}</strong> 条可回溯记录</span>
          </div>
          <p className="growth-source">
            {data.timelineIsDemo ? "示例记录 · " : ""}这里记录孩子真实经历过的过程与变化，不做能力排名。
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
            沿着时间往下看：每一站只记录发生过的行为，作品作为证据单独查看。
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
                  <button className="milestone-open" onClick={(event) => open(item, event.currentTarget)}>查看原始记录 <ExplorerIcon name="arrow" /></button>
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
            新的真实活动会继续沿着星路出现。家长可以回看阶段结论，也可以筛选和保存这段成长记录。
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
          onClose={closeDialog}
          onNavigate={onNavigate}
        />
      )}
    </main>
  );
}
