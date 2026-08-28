"use client";

import {FormEvent, lazy, Suspense, useEffect, useState} from "react";
import PlanetHome from "./components/PlanetHome";
import {getViewFromUrl, urlForView} from "./lib/view-state.mjs";

const WorksPage=lazy(()=>import("./components/WorksPage"));
const GrowthTrailPage=lazy(()=>import("./components/GrowthTrailPage"));

type Role="student"|"adult";
type AdultKind="parent"|"teacher";
type View="planet"|"works"|"treasure"|"report"|"showcase"|"timeline";
type Account={id:string;username:string;display_name:string;age:number;created_at?:string;role:Role;adult_kind?:AdultKind|null};
type Session={account:Account;students:Account[];selected_student:Account|null};
type AuthMode="login"|"register"|"reset";

const CORE_URL="http://localhost:8020";
const REPORT_URL="http://localhost:5175";

function normalizeSession(payload:unknown):Session{
  const value=payload as {account:Account;students?:Account[];selected_student?:Account|null},account=value.account;
  return {account,students:Array.isArray(value.students)?value.students:[],selected_student:value.selected_student??(account.role==="student"?account:null)};
}
async function loadSession(){const response=await fetch(`${CORE_URL}/api/account/me`,{credentials:"include"});if(!response.ok)throw new Error();return normalizeSession(await response.json());}

export default function Home(){
  const [session,setSession]=useState<Session|null|undefined>(undefined);
  const [view,setView]=useState<View>("planet");
  const role=session?.account.role;
  useEffect(()=>{loadSession().then(setSession).catch(()=>setSession(null));},[]);
  useEffect(()=>{if(!role)return;const sync=()=>setView(getViewFromUrl(window.location.href,role) as View);sync();window.addEventListener("popstate",sync);return()=>window.removeEventListener("popstate",sync);},[role]);
  const navigate=(next:View)=>{setView(next);window.history.pushState({view:next},"",urlForView(next,session?.account.role));window.scrollTo({top:0,behavior:"smooth"});};
  const logout=async()=>{await fetch(`${CORE_URL}/api/account/session`,{method:"DELETE",credentials:"include"}).catch(()=>undefined);setSession(null);};
  const selectStudent=async(studentId:string)=>{const response=await fetch(`${CORE_URL}/api/account/context`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({student_id:studentId})});if(response.ok){setSession(await loadSession());setView("report");window.history.replaceState({view:"report"},"",urlForView("report","adult"));}};
  if(session===undefined)return <main className="session-loading" aria-label="正在确认登录状态"/>;
  if(!session)return <AuthPage onAuthenticated={setSession}/>;
  if(session.account.role==="adult"&&!session.selected_student)return <AdultBindingPage session={session} onUpdated={()=>loadSession().then(setSession)} onLogout={logout}/>;
  const subject=session.selected_student??session.account,isAdult=session.account.role==="adult";
  return <main className={`app-shell role-${session.account.role}`}>
    <Header session={session} view={view} onNavigate={navigate} onLogout={logout} onSelectStudent={selectStudent}/>
    {!isAdult&&view==="planet"&&<PlanetHome onNavigate={(next)=>navigate(next==="report"?"treasure":next as View)}/>}
    {!isAdult&&view==="works"&&<Suspense fallback={<PersonalLoading text="正在翻开作品册…"/>}><WorksPage account={subject} onNavigate={(next)=>navigate(next==="timeline"?"planet":next as View)} perspective="student"/></Suspense>}
    {!isAdult&&view==="treasure"&&<ReportFrame mode="child" student={subject}/>}
    {isAdult&&view==="report"&&<ReportFrame mode="adult" student={subject}/>}
    {isAdult&&view==="showcase"&&<Suspense fallback={<PersonalLoading text="正在整理作品展柜…"/>}><WorksPage account={subject} onNavigate={(next)=>navigate(next==="works"?"showcase":next as View)} perspective="adult"/></Suspense>}
    {isAdult&&view==="timeline"&&<Suspense fallback={<PersonalLoading text="正在铺开成长足迹…"/>}><GrowthTrailPage account={subject} onNavigate={(next)=>navigate(next==="works"?"showcase":next==="planet"?"report":next as View)} perspective="adult"/></Suspense>}
  </main>;
}

function PersonalLoading({text}:{text:string}){return <section className="personal-loading"><h1>{text}</h1></section>}
function ReportFrame({mode,student}:{mode:"child"|"adult";student:Account}){return <section className="report-frame-shell" aria-label={mode==="child"?"天赋藏宝图":"天赋报告"}><iframe key={`${mode}-${student.id}`} title={`${student.display_name}的${mode==="child"?"天赋藏宝图":"天赋报告"}`} src={`${REPORT_URL}/?view=${mode}&embedded=1&student=${encodeURIComponent(student.id)}`} allow="clipboard-write"/></section>}

function apiErrorMessage(payload:unknown,fallback:string){if(payload&&typeof payload==="object"&&"detail" in payload){const detail=(payload as {detail?:unknown}).detail;if(typeof detail==="string")return detail;if(Array.isArray(detail)&&typeof detail[0]?.msg==="string")return detail[0].msg.replace(/^Value error,\s*/,"");}return fallback;}

function AuthPage({onAuthenticated}:{onAuthenticated:(session:Session)=>void}){
  const [role,setRole]=useState<Role>("student"),[mode,setMode]=useState<AuthMode>("login"),[showPassword,setShowPassword]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState(""),[loading,setLoading]=useState(false),[created,setCreated]=useState<Session|null>(null);
  const switchMode=(next:AuthMode)=>{setMode(next);setError("");setNotice("");setShowPassword(false);};
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();setLoading(true);setError("");setNotice("");const form=new FormData(event.currentTarget),password=String(form.get("password")||"");
    if(mode!=="login"&&password!==String(form.get("confirmPassword")||"")){setError("两次输入的密码不一致");setLoading(false);return;}
    let endpoint="/api/account/session",body:Record<string,unknown>={username:form.get("username"),password,expected_role:role};
    if(mode==="register"){endpoint="/api/account/register";body={username:String(form.get("username")||"").trim()||null,display_name:form.get("displayName"),age:role==="student"?Number(form.get("age")):null,password,role,adult_kind:role==="adult"?form.get("adultKind"):null,recovery_code:form.get("recoveryCode")};}
    else if(mode==="reset"){endpoint="/api/account/password/reset";body={username:form.get("username"),recovery_code:form.get("recoveryCode"),new_password:password};}
    try{const response=await fetch(`${CORE_URL}${endpoint}`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(apiErrorMessage(data,"操作没有完成，请稍后再试"));if(mode==="reset"){setNotice("密码已重置，请用新密码登录。");setMode("login");return;}const next=normalizeSession(data);if(mode==="register")setCreated(next);else onAuthenticated(next);}catch(cause){setError(cause instanceof Error?cause.message:"暂时无法连接账号服务");}finally{setLoading(false);}
  }
  if(created)return <RegistrationSuccess session={created} onContinue={async()=>{const latest=await loadSession();if(latest.account.role==="adult"&&!latest.selected_student)setCreated(latest);else onAuthenticated(latest);}} onBound={async()=>setCreated(await loadSession())}/>;
  return <main className="login-page"><div className="login-stars" aria-hidden="true"><i/><i/><i/><i/><i/></div><section className="login-panel" aria-labelledby="auth-title">
    <div className="mini-planet" aria-hidden="true"><span/><b>✦</b></div><p className="kicker">AI BOLE · EXPLORER ACCOUNT</p><h1 id="auth-title">{mode==="reset"?"重置登录密码":mode==="register"?"创建探索账号":"欢迎回到探索星球"}</h1>
    <div className="role-choice" role="group" aria-label="选择登录身份"><button type="button" className={role==="student"?"active":""} onClick={()=>{setRole("student");setError("")}}><b>我是学生</b><span>探索、创作、收藏作品</span></button><button type="button" className={role==="adult"?"active":""} onClick={()=>{setRole("adult");setError("")}}><b>我是老师 / 家长</b><span>查看报告、作品与成长</span></button></div>
    <div className="auth-tabs" role="tablist"><button type="button" className={mode==="login"?"active":""} onClick={()=>switchMode("login")}>登录</button><button type="button" className={mode==="register"?"active":""} onClick={()=>switchMode("register")}>注册</button><button type="button" className={mode==="reset"?"active":""} onClick={()=>switchMode("reset")}>忘记密码</button></div>
    <form key={`${mode}-${role}`} onSubmit={submit} aria-busy={loading}>
      <label>{mode==="register"?"账号（可留空自动生成）":"账号"}<input name="username" placeholder={mode==="register"?(role==="student"?"自动生成 S+年份+序号":"自动生成 A+年份+序号"):"请输入账号"} autoComplete="username" required={mode!=="register"} maxLength={30}/></label>
      {mode==="register"&&<><div className="login-inline"><label>{role==="student"?"学生昵称":"姓名 / 称呼"}<input name="displayName" required maxLength={30}/></label>{role==="student"&&<label>年龄<input name="age" type="number" min={4} max={18} required/></label>}</div>{role==="adult"&&<label>身份<select name="adultKind" defaultValue="parent"><option value="parent">家长</option><option value="teacher">老师</option></select></label>}</>}
      {(mode==="register"||mode==="reset")&&<label>六位数字找回码<input name="recoveryCode" inputMode="numeric" pattern="[0-9]{6,12}" minLength={6} maxLength={12} required placeholder="请牢记，用于重置密码"/></label>}
      <label>{mode==="reset"?"新密码":"密码"}<span className="password-field"><input name="password" type={showPassword?"text":"password"} minLength={mode==="login"?4:6} maxLength={72} required autoComplete={mode==="login"?"current-password":"new-password"}/><button type="button" onClick={()=>setShowPassword(v=>!v)}>{showPassword?"隐藏":"显示"}</button></span></label>
      {mode!=="login"&&<label>再次输入密码<input name="confirmPassword" type={showPassword?"text":"password"} minLength={6} maxLength={72} required/></label>}
      {error&&<p className="login-error" role="alert">{error}</p>}{notice&&<p className="login-notice" role="status">{notice}</p>}<button className="primary-button" disabled={loading}>{loading?"正在处理…":mode==="login"?`进入${role==="student"?"学生端":"老师 / 家长端"}`:mode==="register"?"创建账号":"重置密码"}<span>→</span></button>
    </form><p className="auth-footnote">成人注册后只需填写学生账号即可绑定，不需要学生密码；最多可绑定 5 位学生。</p>
  </section></main>;
}

function RegistrationSuccess({session,onContinue,onBound}:{session:Session;onContinue:()=>void;onBound:()=>void}){const isAdult=session.account.role==="adult";return <main className="login-page"><section className="login-panel registration-success"><p className="kicker">ACCOUNT CREATED</p><h1>账号创建成功</h1><p>请保存好登录账号和六位找回码。</p><div className="account-code"><small>{isAdult?"老师 / 家长账号":"学生账号"}</small><strong>{session.account.username.toUpperCase()}</strong><button onClick={()=>navigator.clipboard?.writeText(session.account.username)}>复制账号</button></div>{isAdult&&<BindingForm students={session.students} onBound={onBound}/>}<button className="primary-button" disabled={isAdult&&!session.selected_student} onClick={onContinue}>{isAdult?"进入学生的天赋报告":"进入我的探索星球"}<span>→</span></button>{isAdult&&!session.selected_student&&<p className="auth-footnote">至少绑定一位已有学生后即可进入。</p>}</section></main>}

function BindingForm({students,onBound}:{students:Account[];onBound:()=>void}){const [error,setError]=useState(""),[loading,setLoading]=useState(false);async function bind(event:FormEvent<HTMLFormElement>){event.preventDefault();setLoading(true);setError("");const form=new FormData(event.currentTarget),response=await fetch(`${CORE_URL}/api/account/students/bind`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:form.get("studentUsername")})}),data=await response.json().catch(()=>({}));setLoading(false);if(!response.ok){setError(apiErrorMessage(data,"绑定失败"));return;}event.currentTarget.reset();onBound();}return <section className="binding-box"><h2>绑定学生 <small>{students.length}/5</small></h2><p>输入学生的登录账号即可，不需要学生密码。</p><form onSubmit={bind}><input name="studentUsername" required placeholder="例如 S20260001"/><button disabled={loading||students.length>=5}>{loading?"绑定中…":"添加学生"}</button></form>{error&&<p className="login-error">{error}</p>}<div className="bound-students">{students.map(s=><span key={s.id}><b>{s.display_name}</b><small>{s.username.toUpperCase()}</small></span>)}</div></section>}

function AdultBindingPage({session,onUpdated,onLogout}:{session:Session;onUpdated:()=>void;onLogout:()=>void}){return <main className="login-page"><section className="login-panel registration-success"><h1>先绑定一位学生</h1><p>绑定后才能查看对应学生的报告、作品和成长足迹。</p><BindingForm students={session.students} onBound={onUpdated}/><button className="text-button" onClick={onLogout}>退出登录</button></section></main>}

function Header({session,view,onNavigate,onLogout,onSelectStudent}:{session:Session;view:View;onNavigate:(view:View)=>void;onLogout:()=>void;onSelectStudent:(id:string)=>void}){const adult=session.account.role==="adult",nav:[View,string][]=adult?[["report","天赋报告"],["showcase","作品展柜"],["timeline","成长足迹"]]:[["planet","探索星球"],["works","我的作品"],["treasure","天赋藏宝图"]];return <header className={`topbar ${view!=="planet"?"personal-topbar":""} view-${view}`}><button className="brand" onClick={()=>onNavigate(adult?"report":"planet")}><span className="brand-mark"><img src="/assets/watercolor-brand-planet-v1.png" alt=""/></span><span className="brand-copy"><b>AI 伯乐</b><small><i/>{adult?"老师 / 家长观察站":"儿童天赋探索星球"}</small></span></button><nav>{nav.map(([id,label])=><button key={id} className={view===id?"active":""} onClick={()=>onNavigate(id)}>{label}</button>)}</nav>{adult&&session.students.length>0&&<label className="student-switcher">正在查看<select value={session.selected_student?.id??""} onChange={e=>onSelectStudent(e.target.value)}>{session.students.map(student=><option key={student.id} value={student.id}>{student.display_name} · {student.username.toUpperCase()}</option>)}</select></label>}<details className="profile-menu"><summary><span>{session.account.display_name}</span><b>{session.account.display_name.slice(0,2)}</b></summary><div><strong>{session.account.display_name}</strong><small>@{session.account.username.toUpperCase()}</small><button onClick={onLogout}>退出登录</button></div></details></header>}
