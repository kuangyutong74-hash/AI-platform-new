"use client";

import { FormEvent, lazy, Suspense, useEffect, useState } from "react";
import PlanetHome from "./components/PlanetHome";
import { getViewFromUrl, urlForView } from "./lib/view-state.mjs";

const WorksPage = lazy(() => import("./components/WorksPage"));
const GrowthTrailPage = lazy(() => import("./components/GrowthTrailPage"));

type View = "planet" | "works" | "timeline";
type NavigationView = View | "report";
type Account = {
  id: string;
  username: string;
  display_name: string;
  age: number;
  created_at?: string;
};
type AuthMode = "login" | "register";

const CORE_URL = "http://localhost:8020";
const REPORT_URL = "http://localhost:5175/?from=ai-bole";

export default function Home() {
  const [account, setAccount] = useState<Account | null | undefined>(undefined);
  const [view, setView] = useState<View>("planet");

  useEffect(() => {
    fetch(`${CORE_URL}/api/account/me`, { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        setAccount((await response.json()).account);
      })
      .catch(() => setAccount(null));
  }, []);

  useEffect(() => {
    const syncView = () => setView(getViewFromUrl(window.location.href));
    syncView();
    window.addEventListener("popstate", syncView);
    return () => window.removeEventListener("popstate", syncView);
  }, []);

  const navigate = (next: NavigationView) => {
    if (next === "report") {
      location.href = REPORT_URL;
      return;
    }
    setView(next);
    window.history.pushState({ view: next }, "", urlForView(next));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const logout = async () => {
    await fetch(`${CORE_URL}/api/account/session`, {
      method: "DELETE",
      credentials: "include",
    }).catch(() => undefined);
    setAccount(null);
  };

  if (account === undefined)
    return <main className="session-loading" aria-label="正在确认登录状态" />;
  if (!account) return <AuthPage onAuthenticated={setAccount} />;

  return (
    <main className="app-shell">
      <Header view={view} account={account} onNavigate={navigate} onLogout={logout} />
      {view === "planet" && <PlanetHome onNavigate={navigate} />}
      {view === "works" && (
        <Suspense fallback={<section className="personal-loading"><h1>正在翻开宝藏本…</h1></section>}>
          <WorksPage account={account} onNavigate={navigate} />
        </Suspense>
      )}
      {view === "timeline" && (
        <Suspense fallback={<section className="personal-loading"><h1>正在铺开星光小路…</h1></section>}>
          <GrowthTrailPage account={account} onNavigate={navigate} />
        </Suspense>
      )}
    </main>
  );
}

function apiErrorMessage(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && typeof detail[0]?.msg === "string")
      return detail[0].msg.replace(/^Value error,\s*/, "");
  }
  return fallback;
}

function AuthPage({ onAuthenticated }: { onAuthenticated: (account: Account) => void }) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const switchMode = (next: AuthMode) => {
    setMode(next);
    setError("");
    setShowPassword(false);
  };

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") || "");
    if (mode === "register" && password !== String(form.get("confirmPassword") || "")) {
      setError("两次输入的密码不一致");
      setLoading(false);
      return;
    }
    const body = mode === "register"
      ? { username: form.get("username"), display_name: form.get("displayName"), age: Number(form.get("age")), password }
      : { username: form.get("username"), password };
    try {
      const response = await fetch(
        `${CORE_URL}${mode === "register" ? "/api/account/register" : "/api/account/session"}`,
        { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok)
        throw new Error(apiErrorMessage(data, mode === "register" ? "注册没有完成，请稍后再试" : "登录失败"));
      onAuthenticated(data.account);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "暂时无法连接账号服务");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-stars" aria-hidden="true"><i /><i /><i /><i /><i /></div>
      <section className="login-panel" aria-labelledby="auth-title">
        <div className="mini-planet" aria-hidden="true"><span /><b>✦</b></div>
        <p className="kicker">AI BOLE · EXPLORER ACCOUNT</p>
        <h1 id="auth-title">{mode === "login" ? "欢迎回到探索星球" : "创建你的探索者账号"}</h1>
        <p className="login-lead">
          {mode === "login"
            ? "登录后，四块大陆会继续把作品和成长足迹收藏在你的账号里。"
            : "这个账号会独立保存昵称、作品和每一次完成记录。"}
        </p>
        <div className="auth-tabs" role="tablist" aria-label="账号操作">
          <button type="button" role="tab" aria-selected={mode === "login"} className={mode === "login" ? "active" : ""} onClick={() => switchMode("login")}>登录</button>
          <button type="button" role="tab" aria-selected={mode === "register"} className={mode === "register" ? "active" : ""} onClick={() => switchMode("register")}>注册新账号</button>
        </div>
        <form key={mode} onSubmit={submit} aria-busy={loading}>
          <label>
            探索者账号
            <input name="username" placeholder="请输入账号" autoComplete="username" required minLength={2} maxLength={30} />
          </label>
          {mode === "register" && (
            <div className="login-inline">
              <label>孩子昵称<input name="displayName" placeholder="例如：小航" autoComplete="nickname" required maxLength={30} /></label>
              <label>年龄<input name="age" type="number" min={4} max={18} placeholder="8" inputMode="numeric" required /></label>
            </div>
          )}
          <label>
            探索密码
            <span className="password-field">
              <input name="password" type={showPassword ? "text" : "password"} placeholder={mode === "register" ? "至少 6 位" : "请输入密码"} autoComplete={mode === "register" ? "new-password" : "current-password"} required minLength={mode === "register" ? 6 : 4} maxLength={72} />
              <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "隐藏密码" : "显示密码"}>{showPassword ? "隐藏" : "显示"}</button>
            </span>
          </label>
          {mode === "register" && (
            <label>再输入一次密码<input name="confirmPassword" type={showPassword ? "text" : "password"} placeholder="请再次输入" autoComplete="new-password" required minLength={6} maxLength={72} /></label>
          )}
          {error && <p className="login-error" role="alert">{error}</p>}
          <button className="primary-button" disabled={loading}>
            {loading ? (mode === "login" ? "正在登录…" : "正在创建…") : (mode === "login" ? "进入我的星球" : "创建并开始探索")}
            <span aria-hidden="true">→</span>
          </button>
        </form>
        <p className="auth-footnote">
          {mode === "login" ? "还没有账号？切换到“注册新账号”即可创建。" : "账号和密码只用于识别你的独立探索档案。"}
        </p>
      </section>
    </main>
  );
}

function Header({ view, account, onNavigate, onLogout }: { view: View; account: Account; onNavigate: (view: NavigationView) => void; onLogout: () => void }) {
  return (
    <header className={`topbar ${view !== "planet" ? "personal-topbar" : ""} view-${view}`}>
      <button className="brand" onClick={() => onNavigate("planet")} aria-label="返回AI伯乐探索星球">
        <span className="brand-mark" aria-hidden="true"><img src="/assets/watercolor-brand-planet-v1.png" alt="" /></span>
        <span className="brand-copy"><b>AI 伯乐</b><small><i />儿童天赋探索星球</small></span>
      </button>
      <nav>
        {[["planet", "探索星球"], ["works", "我的作品"], ["timeline", "成长足迹"], ["report", "天赋报告"]].map(([id, label]) => (
          <button key={id} className={view === id ? "active" : ""} onClick={() => onNavigate(id as NavigationView)}>{label}</button>
        ))}
      </nav>
      <details className="profile-menu">
        <summary aria-label={`打开${account.display_name}的账号菜单`}>
          <span>{account.display_name}</span><b aria-hidden="true">{account.display_name.slice(0, 2)}</b>
        </summary>
        <div><strong>{account.display_name}</strong><small>@{account.username} · {account.age} 岁</small><button onClick={onLogout}>退出登录</button></div>
      </details>
    </header>
  );
}
