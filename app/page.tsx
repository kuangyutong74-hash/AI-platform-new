"use client";
import { FormEvent, useEffect, useState } from "react";
import PlanetHome from "./components/PlanetHome";

type View = "planet" | "works" | "timeline";
type NavigationView = View | "report";
type Account = { id:string; username:string; display_name:string; age:number };
const CORE_URL = "http://localhost:8020";
const REPORT_URL = "http://localhost:5175/?from=ai-bole";

export default function Home() {
  const [account,setAccount]=useState<Account|null|undefined>(undefined);
  const [view,setView]=useState<View>("planet");
  useEffect(()=>{fetch(`${CORE_URL}/api/account/me`,{credentials:"include"}).then(async response=>{if(!response.ok)throw new Error();setAccount((await response.json()).account);}).catch(()=>setAccount(null));},[]);
  const navigate=(next:NavigationView)=>{if(next==="report"){location.href=REPORT_URL;return;}setView(next);};
  const logout=async()=>{await fetch(`${CORE_URL}/api/account/session`,{method:"DELETE",credentials:"include"}).catch(()=>undefined);setAccount(null);};
  if(account===undefined)return <main className="session-loading"/>;
  if(!account)return <LoginPage onLogin={setAccount}/>;
  return <main className="app-shell"><Header view={view} account={account} onNavigate={navigate} onLogout={logout}/>
    {view==="planet"&&<PlanetHome onNavigate={navigate}/>} 
    {view==="works"&&<SimplePage title="我的作品" subtitle="四块大陆上的创造，都收藏在这里。" cards={[["故事书","云朵城堡的最后一扇门","来自故事共创"],["设计图","深海能源站重建方案","来自基地重建"],["发现卡","我对动物行为特别好奇","来自聊天观察"],["角色卡","儿童记者的一天","来自职业模拟器"]]}/>} 
    {view==="timeline"&&<SimplePage title="成长足迹" subtitle="不比较快慢，只记录每一次尝试。" cards={[["今天","体验了儿童记者，主动追问了三个问题","职业模拟器"],["昨天","完成深海能源站第二版布局","基地重建"],["8月15日","创造了一个会改变天气的故事角色","故事共创"],["8月14日","聊到了喜欢观察昆虫和云朵","聊天观察"]]}/>} 
  </main>;
}

function LoginPage({onLogin}:{onLogin:(account:Account)=>void}) {
  const [error,setError]=useState(""); const [loading,setLoading]=useState(false);
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setLoading(true);setError("");const form=new FormData(event.currentTarget);try{const response=await fetch(`${CORE_URL}/api/account/session`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:form.get("username"),display_name:form.get("displayName"),age:Number(form.get("age")),password:form.get("password")})});const data=await response.json();if(!response.ok)throw new Error(data.detail||"登录失败");onLogin(data.account);}catch(cause){setError(cause instanceof Error?cause.message:"无法连接统一账号服务");}finally{setLoading(false);}}
  return <main className="login-page"><div className="login-stars" aria-hidden="true"><i/><i/><i/><i/><i/></div><section className="login-panel"><div className="mini-planet"><span/><b>✦</b></div><p className="kicker">AI BOLE · UNIFIED ACCOUNT</p><h1>欢迎来到探索星球</h1><p className="login-lead">一个账号连接四块大陆，作品和成长证据都会回到同一位探索者名下。</p><form onSubmit={submit}><label>探索者账号<input name="username" defaultValue="xiaohang" required minLength={2}/></label><div className="login-inline"><label>孩子昵称<input name="displayName" defaultValue="小小探索家" required/></label><label>年龄<input name="age" type="number" min={4} max={18} defaultValue={9} required/></label></div><label>探索密码<input name="password" type="password" defaultValue="123456" required minLength={4}/></label>{error&&<p className="login-error" role="alert">{error}</p>}<button className="primary-button" disabled={loading}>{loading?"正在连接…":"进入我的星球"}<span>→</span></button></form><p className="demo-note">首次登录会创建账号；以后使用同一账号和密码即可继续探索。</p></section></main>;
}

function Header({view,account,onNavigate,onLogout}:{view:View;account:Account;onNavigate:(v:NavigationView)=>void;onLogout:()=>void}) {return <header className="topbar"><button className="brand" onClick={()=>onNavigate("planet")} aria-label="返回AI伯乐探索星球"><span className="brand-mark" aria-hidden="true"><i/><em>✦</em></span><span className="brand-copy"><b>AI 伯乐</b><small><i/>儿童天赋探索星球</small></span></button><nav>{[["planet","探索星球"],["works","我的作品"],["timeline","成长足迹"],["report","天赋报告"]].map(([id,label])=><button key={id} className={view===id?"active":""} onClick={()=>onNavigate(id as NavigationView)}>{label}</button>)}</nav><div className="profile"><span>{account.display_name}</span><button aria-label="退出登录" title="退出登录" onClick={onLogout}>{account.display_name.slice(0,2)}</button></div></header>}
function SimplePage({title,subtitle,cards}:{title:string;subtitle:string;cards:string[][]}) {return <section className="content-page"><p className="kicker">PERSONAL COLLECTION</p><h1>{title}</h1><p className="page-subtitle">{subtitle}</p><div className="collection-grid">{cards.map(c=><article key={c[1]}><div className="work-placeholder">✦</div><small>{c[0]}</small><h2>{c[1]}</h2><p>{c[2]}</p></article>)}</div></section>}
