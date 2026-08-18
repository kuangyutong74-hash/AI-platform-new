"use client";
import { useEffect, useState } from "react";
import PlanetHome from "./components/PlanetHome";
import { PLATFORM_MODULES as modules } from "./config/modules";
type View = "planet" | "works" | "timeline" | "report";

export default function Home() {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);
  const [view, setView] = useState<View>("planet");
  useEffect(() => { const returning = new URLSearchParams(location.search).has("from"); setLoggedIn(returning || localStorage.getItem("ai-bole-session") === "active"); if (returning) localStorage.setItem("ai-bole-session", "active"); }, []);
  const login = () => { localStorage.setItem("ai-bole-session", "active"); setLoggedIn(true); setView("planet"); };
  const logout = () => { localStorage.removeItem("ai-bole-session"); setLoggedIn(false); };
  if (loggedIn === null) return <main className="session-loading" />;
  if (!loggedIn) return <LoginPage onLogin={login} />;
  return <main className="app-shell"><Header view={view} onNavigate={setView} onLogout={logout}/>
    {view === "planet" && <PlanetHome onNavigate={setView}/>} 
    {view === "works" && <SimplePage title="我的作品" subtitle="四块大陆上的创造，都收藏在这里。" cards={[["故事书","云朵城堡的最后一扇门","来自故事共创"],["设计图","深海能源站重建方案","来自基地重建"],["发现卡","我对动物行为特别好奇","来自聊天观察"],["角色卡","儿童记者的一天","来自职业模拟器"]]}/>} 
    {view === "timeline" && <SimplePage title="成长足迹" subtitle="不比较快慢，只记录每一次尝试。" cards={[["今天","体验了儿童记者，主动追问了三个问题","职业模拟器"],["昨天","完成深海能源站第二版布局","基地重建"],["8月15日","创造了一个会改变天气的故事角色","故事共创"],["8月14日","聊到了喜欢观察昆虫和云朵","聊天观察"]]}/>} 
    {view === "report" && <ReportPage onBack={() => setView("planet")}/>}</main>;
}
function LoginPage({onLogin}:{onLogin:()=>void}) { return <main className="login-page"><div className="login-stars" aria-hidden="true"><i/><i/><i/><i/><i/></div><section className="login-panel"><div className="mini-planet"><span/><b>✦</b></div><p className="kicker">AI BOLE · EXPLORATION PLANET</p><h1>欢迎来到探索星球</h1><p className="login-lead">每一种好奇，都是一块等待发现的新大陆。</p><form onSubmit={e=>{e.preventDefault();onLogin();}}><label>探索者账号<input defaultValue="小小探索家"/></label><label>探索密码<input type="password" defaultValue="123456"/></label><button className="primary-button">进入我的星球 <span>→</span></button></form><div className="login-links"><button type="button">教师登录</button><span>·</span><button type="button">家长入口</button></div><p className="demo-note">当前为平台原型，点击即可体验</p></section></main>; }
function Header({view,onNavigate,onLogout}:{view:View;onNavigate:(v:View)=>void;onLogout:()=>void}) { return <header className="topbar"><button className="brand" onClick={()=>onNavigate("planet")}><span className="brand-mark">✦</span><span><b>AI 伯乐</b><small>探索星球</small></span></button><nav>{[["planet","探索星球"],["works","我的作品"],["timeline","成长足迹"],["report","天赋报告"]].map(([id,label])=><button key={id} className={view===id?"active":""} onClick={()=>onNavigate(id as View)}>{label}</button>)}</nav><div className="profile"><span>小小探索家</span><button aria-label="退出登录" onClick={onLogout}>小航</button></div></header>; }
function SimplePage({title,subtitle,cards}:{title:string;subtitle:string;cards:string[][]}) { return <section className="content-page"><p className="kicker">PERSONAL COLLECTION</p><h1>{title}</h1><p className="page-subtitle">{subtitle}</p><div className="collection-grid">{cards.map(c=><article key={c[1]}><div className="work-placeholder">✦</div><small>{c[0]}</small><h2>{c[1]}</h2><p>{c[2]}</p></article>)}</div></section>; }
function ReportPage({onBack}:{onBack:()=>void}) { return <section className="report-page"><div className="report-heading"><div><p className="kicker">MY DISCOVERY MAP</p><h1>我的探索星图</h1><p>根据四类活动形成的阶段性兴趣与优势线索</p></div><button onClick={onBack}>返回探索星球</button></div><div className="report-notice"><span>✦</span><p><b>这不是一次考试，也不是固定标签。</b><br/>报告记录你在不同活动中的选择、作品和方法，帮助你继续发现自己。</p></div><div className="report-layout"><article className="report-main"><h2>最近被点亮的星光</h2><div className="signal-list"><div><b>想象与表达</b><p>在故事活动中主动增加人物关系和情节转折。</p><small>证据来自：故事共创 · 3次活动</small></div><div><b>空间与建造</b><p>遇到结构问题后愿意调整方案，并尝试不同布局。</p><small>证据来自：基地重建 · 2次活动</small></div></div></article><aside className="report-side"><h2>探索覆盖</h2>{modules.map((m,i)=><div className="coverage" key={m.id}><span>{m.module}</span><i><b style={{width:`${[72,84,63,58][i]}%`}}/></i><small>{["5次记录","3个作品","2次任务","2种职业"][i]}</small></div>)}</aside></div></section>; }
