"use client";

import {FormEvent, lazy, Suspense, useEffect, useState} from "react";
import PlanetHome from "./components/PlanetHome";
import {getViewFromUrl, urlForView} from "./lib/view-state.mjs";

const WorksPage=lazy(()=>import("./components/WorksPage"));
const GrowthTrailPage=lazy(()=>import("./components/GrowthTrailPage"));

type Role="student"|"adult";
type View="planet"|"works"|"treasure"|"report"|"showcase"|"timeline";
type Account={id:string;username:string;display_name:string;age:number;created_at?:string;role:Role};
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
  const [studentManagerOpen,setStudentManagerOpen]=useState(false);
  const role=session?.account.role;
  useEffect(()=>{loadSession().then(setSession).catch(()=>setSession(null));},[]);
  useEffect(()=>{if(!role)return;const sync=()=>setView(getViewFromUrl(window.location.href,role) as View);sync();window.addEventListener("popstate",sync);return()=>window.removeEventListener("popstate",sync);},[role]);
  const navigate=(next:View)=>{setView(next);window.history.pushState({view:next},"",urlForView(next,session?.account.role));window.scrollTo({top:0,behavior:"smooth"});};
  const logout=async()=>{await fetch(`${CORE_URL}/api/account/session`,{method:"DELETE",credentials:"include"}).catch(()=>undefined);setStudentManagerOpen(false);setSession(null);};
  const selectStudent=async(studentId:string)=>{const response=await fetch(`${CORE_URL}/api/account/context`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({student_id:studentId})});if(response.ok){setSession(await loadSession());setView("report");window.history.replaceState({view:"report"},"",urlForView("report","adult"));}};
  if(session===undefined)return <main className="session-loading" aria-label="正在确认登录状态"/>;
  if(!session)return <AuthPage onAuthenticated={setSession}/>;
  const isAdult=session.account.role==="adult";
  const subject=isAdult?session.selected_student:session.account;
  return <main className={`app-shell role-${session.account.role}`}>
    <Header session={session} view={view} onNavigate={navigate} onLogout={logout} onSelectStudent={selectStudent} onManageStudents={()=>setStudentManagerOpen(true)}/>
    {isAdult&&studentManagerOpen&&<StudentManager
      session={session}
      onClose={()=>setStudentManagerOpen(false)}
      onChanged={next=>{setSession(next);if(next.selected_student){setStudentManagerOpen(false);setView("report");window.history.replaceState({view:"report"},"",urlForView("report","adult"));}}}
    />}
    {isAdult&&!subject&&<AdultEmptyState session={session} onManageStudents={()=>setStudentManagerOpen(true)}/>}
    {!isAdult&&view==="planet"&&<PlanetHome onNavigate={(next)=>navigate(next==="report"?"treasure":next as View)}/>}
    {!isAdult&&subject&&view==="works"&&<Suspense fallback={<PersonalLoading text="正在翻开作品册…"/>}><WorksPage account={subject} onNavigate={(next)=>navigate(next==="timeline"?"planet":next as View)} perspective="student"/></Suspense>}
    {!isAdult&&subject&&view==="treasure"&&<ReportFrame mode="child" student={subject}/>}
    {isAdult&&subject&&view==="report"&&<ReportFrame mode="adult" student={subject}/>}
    {isAdult&&subject&&view==="showcase"&&<Suspense fallback={<PersonalLoading text="正在整理作品展柜…"/>}><WorksPage account={subject} onNavigate={(next)=>navigate(next==="works"?"showcase":next as View)} perspective="adult"/></Suspense>}
    {isAdult&&subject&&view==="timeline"&&<Suspense fallback={<PersonalLoading text="正在铺开成长足迹…"/>}><GrowthTrailPage account={subject} onNavigate={(next)=>navigate(next==="works"?"showcase":next==="planet"?"report":next as View)} perspective="adult"/></Suspense>}
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
    if(mode==="register"){endpoint="/api/account/register";body={username:String(form.get("username")||"").trim()||null,display_name:form.get("displayName"),age:role==="student"?Number(form.get("age")):null,password,role};}
    else if(mode==="reset"){endpoint="/api/account/password/reset";body={username:form.get("username"),new_password:password};}
    try{const response=await fetch(`${CORE_URL}${endpoint}`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(apiErrorMessage(data,"操作没有完成，请稍后再试"));if(mode==="reset"){setNotice("密码已重置，请用新密码登录。");setMode("login");return;}const next=normalizeSession(data);if(mode==="register")setCreated(next);else onAuthenticated(next);}catch(cause){setError(cause instanceof Error?cause.message:"暂时无法连接账号服务");}finally{setLoading(false);}
  }
  if(created)return <RegistrationSuccess session={created} onContinue={async()=>onAuthenticated(await loadSession())} onBound={setCreated} onLogout={async()=>{await fetch(`${CORE_URL}/api/account/session`,{method:"DELETE",credentials:"include"}).catch(()=>undefined);setCreated(null);setMode("login");}}/>;
  return <main className="login-page"><div className="login-stars" aria-hidden="true"><i/><i/><i/><i/><i/></div><section className="login-panel" aria-labelledby="auth-title">
    <div className="mini-planet" aria-hidden="true"><span/><b>✦</b></div><p className="kicker">AI BOLE · EXPLORER ACCOUNT</p><h1 id="auth-title">{mode==="reset"?"重置登录密码":mode==="register"?"创建探索账号":"欢迎回到探索星球"}</h1>
    {mode!=="reset"&&<div className="role-choice" role="group" aria-label="选择登录身份"><button type="button" className={role==="student"?"active":""} onClick={()=>{setRole("student");setError("")}}><b>我是学生</b><span>探索、创作、收藏作品</span></button><button type="button" className={role==="adult"?"active":""} onClick={()=>{setRole("adult");setError("")}}><b>我是老师 / 家长</b><span>查看报告、作品与成长</span></button></div>}
    <div className="auth-tabs" role="tablist"><button type="button" className={mode==="login"?"active":""} onClick={()=>switchMode("login")}>登录</button><button type="button" className={mode==="register"?"active":""} onClick={()=>switchMode("register")}>注册</button><button type="button" className={mode==="reset"?"active":""} onClick={()=>switchMode("reset")}>忘记密码</button></div>
    <form key={`${mode}-${role}`} onSubmit={submit} aria-busy={loading}>
      <label>{mode==="register"?"账号（可留空自动生成）":"账号"}<input name="username" placeholder={mode==="register"?(role==="student"?"自动生成 S+年份+序号":"自动生成 A+年份+序号"):"请输入账号"} autoComplete="username" required={mode!=="register"} maxLength={30}/></label>
      {mode==="register"&&<div className={`login-inline ${role==="adult"?"single":""}`}><label>{role==="student"?"学生昵称":"姓名 / 称呼"}<input name="displayName" required maxLength={30}/></label>{role==="student"&&<label>年龄<input name="age" type="number" min={4} max={18} required/></label>}</div>}
      <label>{mode==="reset"?"新密码":"密码"}<span className="password-field"><input name="password" type={showPassword?"text":"password"} minLength={mode==="login"?4:6} maxLength={72} required autoComplete={mode==="login"?"current-password":"new-password"}/><button type="button" onClick={()=>setShowPassword(v=>!v)}>{showPassword?"隐藏":"显示"}</button></span></label>
      {mode!=="login"&&<label>再次输入密码<input name="confirmPassword" type={showPassword?"text":"password"} minLength={6} maxLength={72} required/></label>}
      {error&&<p className="login-error" role="alert">{error}</p>}{notice&&<p className="login-notice" role="status">{notice}</p>}<button className="primary-button" disabled={loading}>{loading?"正在处理…":mode==="login"?`进入${role==="student"?"学生端":"老师 / 家长端"}`:mode==="register"?"创建账号":"重置密码"}<span>→</span></button>
    </form><p className="auth-footnote">{mode==="reset"?"输入用户名并设置新密码即可完成重置。":"成人注册后只需填写学生账号即可绑定，不需要学生密码；最多可绑定 5 位学生。"}</p>
  </section></main>;
}

function RegistrationSuccess({session,onContinue,onBound,onLogout}:{session:Session;onContinue:()=>void;onBound:(session:Session)=>void;onLogout:()=>void}){const isAdult=session.account.role==="adult";return <main className="login-page"><section className="login-panel registration-success"><p className="kicker">ACCOUNT CREATED</p><h1>账号创建成功</h1><p>请保存好登录账号和密码。</p><div className="account-code"><small>{isAdult?"家长 / 老师账号":"学生账号"}</small><strong>{session.account.username.toUpperCase()}</strong><button onClick={()=>navigator.clipboard?.writeText(session.account.username)}>复制账号</button></div>{isAdult&&<BindingForm students={session.students} onChanged={onBound}/>}<button className="primary-button" onClick={onContinue}>{isAdult?(session.selected_student?"进入学生的天赋报告":"暂不绑定，进入家长 / 老师端"):"进入我的探索星球"}<span>→</span></button><button className="text-button" onClick={onLogout}>退出登录</button>{isAdult&&!session.selected_student&&<p className="auth-footnote">没有学生账号也可以先进入，之后再绑定。</p>}</section></main>}

function BindingForm({students,onChanged}:{students:Account[];onChanged:(session:Session)=>void}){
  const [error,setError]=useState(""),[loading,setLoading]=useState(false);
  async function bind(event:FormEvent<HTMLFormElement>){
    event.preventDefault();
    const formElement=event.currentTarget,form=new FormData(formElement);
    setLoading(true);setError("");
    try{
      const response=await fetch(`${CORE_URL}/api/account/students/bind`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:form.get("studentUsername")})});
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(apiErrorMessage(data,"绑定失败"));
      formElement.reset();
      onChanged(normalizeSession(data));
    }catch(cause){setError(cause instanceof Error?cause.message:"绑定失败");}finally{setLoading(false);}
  }
  async function unbind(student:Account){
    if(!window.confirm(`确定解除与“${student.display_name}”的绑定吗？`))return;
    setLoading(true);setError("");
    try{
      const response=await fetch(`${CORE_URL}/api/account/students/${encodeURIComponent(student.id)}`,{method:"DELETE",credentials:"include"});
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(apiErrorMessage(data,"解除绑定失败"));
      onChanged(normalizeSession(data));
    }catch(cause){setError(cause instanceof Error?cause.message:"解除绑定失败");}finally{setLoading(false);}
  }
  return <section className="binding-box"><h2>管理学生 <small>{students.length}/5</small></h2><p>输入学生登录账号即可绑定，不需要学生密码。</p><form onSubmit={bind}><input name="studentUsername" required placeholder="例如 S20260001"/><button disabled={loading||students.length>=5}>{loading?"处理中…":"添加学生"}</button></form>{error&&<p className="login-error" role="alert">{error}</p>}<div className="bound-students">{students.map(student=><span key={student.id}><span><b>{student.display_name}</b><small>{student.username.toUpperCase()}</small></span><button type="button" disabled={loading} onClick={()=>unbind(student)}>解除</button></span>)}</div></section>;
}

function StudentManager({session,onClose,onChanged}:{session:Session;onClose:()=>void;onChanged:(session:Session)=>void}){return <div className="student-manager-backdrop"><section className="student-manager" role="dialog" aria-modal="true" aria-labelledby="student-manager-title"><header><div><p>STUDENT MANAGEMENT</p><h2 id="student-manager-title">学生管理</h2></div><button type="button" aria-label="关闭学生管理" onClick={onClose}>×</button></header><BindingForm students={session.students} onChanged={onChanged}/></section></div>}

function AdultEmptyState({session,onManageStudents}:{session:Session;onManageStudents:()=>void}){return <section className="adult-empty-state"><div><p className="kicker">家长 / 老师观察站</p><h1>欢迎，{session.account.display_name}</h1><p>这里还没有学生档案。添加学生后，报告、作品和成长足迹会立即出现在这里。</p><button className="empty-state-action" onClick={onManageStudents}>添加第一位学生</button><p className="auth-footnote">现在也可以通过右上角头像退出，或之后再回来添加。</p></div></section>}

function Header({session,view,onNavigate,onLogout,onSelectStudent,onManageStudents}:{session:Session;view:View;onNavigate:(view:View)=>void;onLogout:()=>void;onSelectStudent:(id:string)=>void;onManageStudents:()=>void}){const adult=session.account.role==="adult",nav:[View,string][]=adult?(session.selected_student?[["report","天赋报告"],["showcase","作品展柜"],["timeline","成长足迹"]]:[]):[["planet","探索星球"],["works","我的作品"],["treasure","天赋藏宝图"]];return <header className={`topbar ${view!=="planet"?"personal-topbar":""} view-${view}`}><button className="brand" onClick={()=>onNavigate(adult?"report":"planet")}><span className="brand-mark"><img src="/assets/watercolor-brand-planet-v1.png" alt=""/></span><span className="brand-copy"><b>AI 伯乐</b><small><i/>{adult?"家长 / 老师观察站":"儿童天赋探索星球"}</small></span></button><nav>{nav.map(([id,label])=><button key={id} className={view===id?"active":""} onClick={()=>onNavigate(id)}>{label}</button>)}</nav><div className="topbar-actions">{adult&&session.students.length>0&&<label className="student-switcher"><span>正在查看</span><select value={session.selected_student?.id??""} onChange={e=>onSelectStudent(e.target.value)}>{session.students.map(student=><option key={student.id} value={student.id}>{student.display_name} · {student.username.toUpperCase()}</option>)}</select></label>}{adult&&<button className="manage-students-button" onClick={onManageStudents}>管理学生</button>}<details className="profile-menu"><summary aria-label="打开账号菜单"><b>{session.account.display_name.slice(0,2)}</b><span>{session.account.display_name}</span></summary><div><strong>{session.account.display_name}</strong><small>@{session.account.username.toUpperCase()}</small>{adult&&<button onClick={onManageStudents}>管理学生</button>}<button onClick={onLogout}>退出登录</button></div></details></div></header>}
