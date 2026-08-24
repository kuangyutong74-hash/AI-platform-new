"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ExplorerIcon from "./ExplorerIcon";
import useExplorerCollection from "../hooks/useExplorerCollection";
import type { ExplorerItem } from "../lib/explorer-types";

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
          aria-label="合上使用历程手账"
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
            {isDemo ? "示例使用历程" : "我的真实使用历程"} ·{" "}
            {formatDate(item.occurredAt)}
          </p>
          <h2 id="trail-dialog-title">{item.title}</h2>
          <p className="memory-heading">这一站的使用小结</p>
          <p className="memory-note">{item.detail}</p>
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
              看看高光作品
            </button>
            <button
              className="plain-button"
              onClick={() => onNavigate("planet")}
            >
              <ExplorerIcon name="compass" />
              再次去探索
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
}: {
  account: Account;
  onNavigate: (view: NavigationView) => void;
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
        <h1>正在整理你的使用历程…</h1>
        <p>从注册那天开始，每一次到访都在赶来和你见面。</p>
      </section>
    );
  const milestones = data.milestones.slice(0, 8);
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
          回探索星球
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
              <span>{data.account.displayName}的星空</span>
              <span>漫游足迹</span>
            </h1>
            <ExplorerIcon name="spark" size={28} />
          </div>
          <p className="growth-promise">从第一天出发，看见自己走过的路。</p>
          <p className="growth-summary">
            从注册起点出发，你已经点亮了 <strong>{usedModuleCount}</strong>{" "}
            座探索大陆。
          </p>
          <p className="growth-source">
            {data.timelineIsDemo
              ? "示例使用历程 · 真实记录会从你的注册日开始"
              : "账号注册与四个探索模块的真实使用小结"}
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
      <section
        className="growth-trail"
        aria-label={`${data.account.displayName}的成长星路`}
      >
        <div className="growth-intro">
          <ExplorerIcon name="spark" />
          <p>
            第一站，是你来到探索星球的那一天。
            <br />
            往后每一站，都记录一座大陆陪你走了多久。
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
                  aria-label={`${item.island}：${item.title}${item.unlocked ? "，打开使用小结" : "，查看点亮提示"}`}
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
                    ? `${item.kind === "registration" ? "注册于" : "最近使用"} ${formatDate(item.occurredAt)}`
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
                  {item.unlocked ? "打开这页使用小结" : "看看怎样点亮"}
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
          <h2>从第一颗星到今天，每一次到访都有自己的位置</h2>
          <p>
            这里从注册日开始，整理了 {usedModuleCount} 座已使用大陆的次数和时间。
            新的探索会继续补进这本历程手账。
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
          onClose={closeDialog}
          onNavigate={onNavigate}
        />
      )}
    </main>
  );
}
