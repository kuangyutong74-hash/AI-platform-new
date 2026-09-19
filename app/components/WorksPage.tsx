"use client";

import {FormEvent,useEffect,useMemo,useRef,useState} from "react";
import ExplorerIcon from "./ExplorerIcon";
import useExplorerCollection from "../hooks/useExplorerCollection";
import {MODULE_META} from "../lib/explorer-data.mjs";
import type {ExplorerItem,ExplorerModule} from "../lib/explorer-types";
import {CORE_API_URL,NATURAL_TTS_URL,PLATFORM_MODULES,canonicalModuleId,launchPlatformModule} from "../config/modules";

type Account={display_name:string;age:number;created_at?:string};
type NavigationView="planet"|"works"|"timeline"|"report";
type WorkModule=Exclude<ExplorerModule,"registration">;
const CORE_URL=CORE_API_URL;
const moduleOrder:WorkModule[]=["story","deep_sea","career","chat"];
const iconByModule:Record<WorkModule,"book"|"waves"|"map"|"journal">={story:"book",deep_sea:"waves",career:"map",chat:"journal"};
const moduleNames:Record<WorkModule,string>={story:MODULE_META.story.name,deep_sea:MODULE_META.deep_sea.name,career:MODULE_META.career.name,chat:MODULE_META.chat.name};
const workTypeOptions:Record<WorkModule,Array<{value:string;label:string}>>={
  story:[{value:"full_story",label:"完整故事"},{value:"story_fragment",label:"故事片段"},{value:"character_profile",label:"角色设定"},{value:"story_illustration",label:"故事插画"},{value:"other",label:"其他创作"}],
  deep_sea:[{value:"base_design",label:"基地设计"},{value:"mission_record",label:"闯关记录"},{value:"solution_sketch",label:"方案草图"},{value:"observation_note",label:"观察笔记"},{value:"other",label:"其他创作"}],
  career:[{value:"career_card",label:"职业体验卡"},{value:"mission_plan",label:"任务方案"},{value:"role_diary",label:"角色日记"},{value:"career_research",label:"职业小调查"},{value:"other",label:"其他创作"}],
  chat:[{value:"mood_note",label:"心情小记"},{value:"opinion",label:"观点表达"},{value:"conversation_inspiration",label:"聊天启发"},{value:"life_observation",label:"生活观察"},{value:"other",label:"其他创作"}],
};
const relayCopy:Record<WorkModule,Record<WorkModule,string>>={
  story:{story:"换一种主题继续写",deep_sea:"把故事里的世界设计成一座深海基地",career:"体验故事主角可能需要的职业",chat:"聊聊主角的选择和我的感受"},
  deep_sea:{story:"把这次建造写成一段冒险故事",deep_sea:"继续改进这座基地",career:"体验负责这座基地的职业",chat:"说说我在建造中遇到的难题"},
  career:{story:"把这次职业体验改编成故事",deep_sea:"为这个职业设计一座工作基地",career:"挑战另一种职业任务",chat:"聊聊我喜欢和不喜欢的工作环节"},
  chat:{story:"把这次聊天里的灵感写成故事",deep_sea:"把我的想法做成一座主题基地",career:"寻找和这个兴趣有关的职业",chat:"沿着这个话题继续探索"},
};

type SpeechPhase="idle"|"loading"|"playing"|"error";

function cleanSpeechText(text:string){return text.replace(/[“”「」『』]/g,"").replace(/([！。？，、])\1+/g,"$1").replace(/\s+/g," ").trim();}

function useNaturalSpeech(){
  const audioRef=useRef<HTMLAudioElement|null>(null),runRef=useRef(0);
  const [phase,setPhase]=useState<SpeechPhase>("idle"),[activeKey,setActiveKey]=useState<string|null>(null);
  const stop=()=>{runRef.current+=1;if(audioRef.current){audioRef.current.pause();audioRef.current.src="";audioRef.current=null;}if("speechSynthesis" in window)window.speechSynthesis.cancel();setPhase("idle");setActiveKey(null);};
  useEffect(()=>stop,[]);
  const fallback=(text:string,key:string,run:number)=>{
    if(run!==runRef.current||!("speechSynthesis" in window)){setPhase("error");setTimeout(()=>{if(run===runRef.current)stop();},4000);return;}
    const utterance=new SpeechSynthesisUtterance(text),voices=window.speechSynthesis.getVoices();
    utterance.voice=voices.find(voice=>/xiaoxiao|xiaoyi|xiaohan|yunxi|晓晓|晓伊|云希/i.test(voice.name))||voices.find(voice=>/^zh/i.test(voice.lang))||null;
    utterance.lang="zh-CN";utterance.rate=.94;utterance.pitch=1.02;
    utterance.onend=()=>{if(run===runRef.current){setPhase("idle");setActiveKey(null);}};
    utterance.onerror=()=>{if(run===runRef.current){setPhase("error");setTimeout(()=>{if(run===runRef.current)stop();},4000);}};
    setPhase("playing");setActiveKey(key);window.speechSynthesis.speak(utterance);
  };
  const toggle=(rawText:string,key:string)=>{
    if(activeKey===key&&(phase==="loading"||phase==="playing")){stop();return;}
    stop();const text=cleanSpeechText(rawText);if(!text)return;
    const run=runRef.current,params=new URLSearchParams({text,voice:"zh-CN-XiaoxiaoNeural",rate:"-6%",pitch:"+2Hz",volume:"+0%"});
    const audio=new Audio(`${NATURAL_TTS_URL}?${params.toString()}`);audioRef.current=audio;audio.preload="auto";setActiveKey(key);setPhase("loading");
    let didFallback=false;const useFallback=()=>{if(didFallback||run!==runRef.current)return;didFallback=true;audioRef.current=null;fallback(text,key,run);};
    audio.onplaying=()=>{if(run===runRef.current)setPhase("playing");};
    audio.onended=()=>{if(run===runRef.current){audioRef.current=null;setPhase("idle");setActiveKey(null);}};
    audio.onerror=useFallback;audio.play().catch(useFallback);
  };
  const label=(key:string,defaultLabel:string)=>activeKey!==key?defaultLabel:phase==="loading"?"正在准备…":phase==="playing"?"停止朗读":phase==="error"?"语音暂时不可用":defaultLabel;
  return {toggle,label,phase,activeKey};
}
function formatDate(value:string){const date=new Date(value);if(Number.isNaN(date.valueOf())||date.valueOf()===0)return "最近一次探索";return new Intl.DateTimeFormat("zh-CN",{year:"numeric",month:"long",day:"numeric"}).format(date);}

export default function WorksPage({account,onNavigate,perspective="student"}:{account:Account;onNavigate:(view:NavigationView)=>void;perspective?:"student"|"adult"}){
  const {data,loading,error,retry,refresh}=useExplorerCollection(account);
  const [section,setSection]=useState<WorkModule|null>(null),[selected,setSelected]=useState<ExplorerItem|null>(null),[largeText,setLargeText]=useState(false);
  const [comment,setComment]=useState(""),[commentError,setCommentError]=useState(""),[submitting,setSubmitting]=useState(false);
  const [manualOpen,setManualOpen]=useState(false),[manualError,setManualError]=useState(""),[manualLoading,setManualLoading]=useState(false);
  const [relayError,setRelayError]=useState(""),[relayLoading,setRelayLoading]=useState<WorkModule|null>(null);
  const [manualModule,setManualModule]=useState<WorkModule>("story");
  const speech=useNaturalSpeech();
  const grouped=useMemo(()=>Object.fromEntries(moduleOrder.map(key=>[key,data?.works.filter(item=>item.module===key)??[]])) as Record<WorkModule,ExplorerItem[]>,[data]);
  if(loading||!data)return <section className="personal-loading" aria-live="polite"><span className="loading-star"><ExplorerIcon name="spark" size={38}/></span><h1>正在整理作品…</h1><p>四座大陆正在把完成成果送回作品册。</p></section>;
  const adult=perspective==="adult";
  const openSection=(key:WorkModule)=>{setSection(key);setSelected(null);window.scrollTo({top:0,behavior:"smooth"});};
  async function submitComment(event:FormEvent){event.preventDefault();if(!selected||!comment.trim())return;setSubmitting(true);setCommentError("");try{const response=await fetch(`${CORE_URL}/api/explorer/comments`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({work_id:selected.id,body:comment})});const payload=await response.json().catch(()=>({}));if(!response.ok)throw new Error(typeof payload.detail==="string"?payload.detail:"点评没有保存成功");const item=payload.comment;setSelected({...selected,comments:[...selected.comments,{id:item.id,body:item.body,authorName:item.author_name,authorKind:item.author_kind,createdAt:item.created_at}]});setComment("");refresh();}catch(cause){setCommentError(cause instanceof Error?cause.message:"点评没有保存成功");}finally{setSubmitting(false);}}
  async function submitManualWork(event:FormEvent<HTMLFormElement>){event.preventDefault();const formElement=event.currentTarget,form=new FormData(formElement);setManualLoading(true);setManualError("");try{const response=await fetch(`${CORE_URL}/api/explorer/works`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({module:form.get("module"),work_type:form.get("work_type"),title:form.get("title"),description:form.get("description")})});const payload=await response.json().catch(()=>({}));if(!response.ok)throw new Error(typeof payload.detail==="string"?payload.detail:"作品没有添加成功");formElement.reset();setManualModule("story");setManualOpen(false);refresh();}catch(cause){setManualError(cause instanceof Error?cause.message:"作品没有添加成功");}finally{setManualLoading(false);}}
  async function deleteManualWork(){if(!selected||selected.kind!=="manual_work"||!window.confirm(`确定删除“${selected.title}”吗？`))return;const response=await fetch(`${CORE_URL}/api/explorer/works/${encodeURIComponent(selected.id)}`,{method:"DELETE",credentials:"include"});if(response.ok){setSelected(null);refresh();}else{const payload=await response.json().catch(()=>({}));setCommentError(typeof payload.detail==="string"?payload.detail:"作品没有删除成功");}}
  async function continueAcrossModule(target:WorkModule){if(!selected||relayLoading)return;const module=PLATFORM_MODULES.find(item=>canonicalModuleId(item.id)===target);if(!module){setRelayError("这座大陆暂时没有开放");return;}setRelayError("");setRelayLoading(target);try{await launchPlatformModule(module,{fromModule:selected.module,sourceTitle:selected.title,prompt:relayCopy[selected.module as WorkModule][target]});}catch(cause){setRelayError(cause instanceof Error?cause.message:"探索接力暂时无法开始");setRelayLoading(null);}}
  if(selected)return <section className={`works-view works-detail tone-${selected.tone}`}><div className="works-sky" aria-hidden="true"/><header className="personal-page-header"><button className="paper-action" onClick={()=>setSelected(null)}><ExplorerIcon name="arrow"/>返回{adult?"作品展柜":"作品列表"}</button><div><span className="header-icon"><ExplorerIcon name={iconByModule[selected.module as WorkModule]} size={27}/></span><h1>{selected.title}</h1><p>{selected.island} · {formatDate(selected.occurredAt)} {selected.isHighlight&&"· 高光作品"}</p></div><button className="listen-action" aria-pressed={speech.activeKey==="work-full"&&speech.phase==="playing"} onClick={()=>speech.toggle(`${selected.title}。${selected.detail}。${selected.quote}`,"work-full")}><ExplorerIcon name="headphones"/>{speech.label("work-full","听一听")}</button></header>
    <main className={`work-reader ${largeText?"is-large":""}`}><div className="reader-scene">{selected.snapshotUrl?<img src={selected.snapshotUrl} alt={`${selected.title}完成画面`}/>:<img src={selected.scene} alt={`${selected.collection}作品贴纸`}/>}<span>{selected.status}</span></div><article><div className="reader-toolbar"><button onClick={()=>setLargeText(v=>!v)}>字 {largeText?"小一点":"大一点"}</button><button aria-pressed={speech.activeKey==="work-page"&&speech.phase==="playing"} onClick={()=>speech.toggle(`${selected.title}。${selected.detail}`,"work-page")}><ExplorerIcon name="headphones" size={17}/>{speech.label("work-page","朗读这一页")}</button></div><p className="reader-date">{formatDate(selected.occurredAt)} · {data.worksAreDemo?"示例作品":"真实完成作品"}</p><h2>{selected.title}</h2><p className="reader-body">{selected.detail}</p>{selected.quote&&<blockquote>“{selected.quote.replace(/[“”]/g,"")}”</blockquote>}<div className="highlight-metric"><span>{selected.metricLabel}</span><strong>{selected.metricValue}</strong></div>{selected.isHighlight&&<div className="reader-note"><ExplorerIcon name="spark"/><p><b>为什么它会成为高光</b><span>{selected.highlightReason}</span></p></div>}
      <section className="work-relay" aria-label="探索接力"><h3>把这件作品带到下一座大陆</h3><p>{adult?"可以和孩子约定下一站，让同一个灵感在不同体验中继续生长。":"不用从头开始，带着这件作品里的灵感继续探索。"}</p>{!adult&&<div>{moduleOrder.filter(target=>target!==selected.module).map(target=><button key={target} disabled={Boolean(relayLoading)} onClick={()=>continueAcrossModule(target)}><ExplorerIcon name={iconByModule[target]}/><span><b>{moduleNames[target]}</b><small>{relayCopy[selected.module as WorkModule][target]}</small></span><i>{relayLoading===target?"正在出发…":"去接力 →"}</i></button>)}</div>}{relayError&&<p className="login-error" role="alert">{relayError}</p>}</section>
      <section className="work-comments" aria-label="家长和老师点评"><h3>温暖点评 <small>{selected.comments.length} 条</small></h3>{selected.comments.length?<div className="comment-list">{selected.comments.map(item=><article key={item.id}><b>{item.authorName}<small>家长 / 老师</small></b><p>{item.body}</p><time>{formatDate(item.createdAt)}</time></article>)}</div>:<p className="comments-empty">还没有点评，完成作品本身就值得好好收藏。</p>}{adult&&!data.worksAreDemo&&<form onSubmit={submitComment}><label htmlFor="work-comment">写下具体、鼓励性的观察</label><textarea id="work-comment" value={comment} onChange={e=>setComment(e.target.value)} maxLength={300} required placeholder="例如：我注意到你遇到困难后换了一种方法，这份坚持很珍贵。"/><div><span>{comment.length}/300</span><button disabled={submitting||!comment.trim()}>{submitting?"正在保存…":"发表点评"}</button></div>{commentError&&<p className="login-error">{commentError}</p>}</form>}</section>
      <div className="reader-actions"><button className="gold-button" onClick={()=>onNavigate(adult?"timeline":"planet")}><ExplorerIcon name="compass"/>{adult?"看看成长足迹":"回到探索星球"}</button>{!adult&&selected.kind==="manual_work"&&<button className="delete-work-button" onClick={deleteManualWork}>删除这件作品</button>}</div></article></main></section>;
  if(section){const meta=MODULE_META[section],items=grouped[section];return <section className={`works-view works-collection tone-${meta.tone}`}><div className="works-sky" aria-hidden="true"/><header className="personal-page-header"><button className="paper-action" onClick={()=>setSection(null)}><ExplorerIcon name="arrow"/>回到作品总览</button><div><span className="header-icon"><ExplorerIcon name={iconByModule[section]} size={27}/></span><h1>{moduleNames[section]}</h1><p>共收藏 {items.length} 件作品，高光作品会显示星标。</p></div><strong>{items.length} 件<small>分类作品</small></strong></header><nav className="collection-tabs" aria-label="作品分类">{moduleOrder.map(key=><button key={key} className={key===section?"active":""} onClick={()=>openSection(key)}><ExplorerIcon name={iconByModule[key]}/><span>{moduleNames[key]}</span></button>)}</nav><main className="collection-stage"><div className="collection-art"><img src={meta.scene} alt=""/><p><ExplorerIcon name="spark"/>高光作品自动收藏，其他成果由你完成后决定是否添加。</p></div><div className="work-list">{items.length?items.map((item,index)=><button className="work-ticket" key={item.id} onClick={()=>setSelected(item)}><span className="ticket-number">{item.isHighlight?"★":String(index+1).padStart(2,"0")}</span><span><small>{formatDate(item.occurredAt)} · {item.status}</small><b>{item.title}</b><p>{item.summary}</p><em>{item.metricLabel} · {item.metricValue}{item.comments.length?` · ${item.comments.length} 条点评`:""}</em></span><i><ExplorerIcon name="arrow"/></i></button>):<div className="collection-empty"><ExplorerIcon name="spark" size={34}/><h2>这里正在等第一件作品</h2><p>完成一次{moduleNames[section]}后，可以收藏成果；高光会自动点亮。</p></div>}</div></main></section>}
  return <section className="works-view works-home"><div className="works-sky" aria-hidden="true"/><header className="works-welcome"><button className="back-to-planet" onClick={()=>onNavigate(adult?"report":"planet")}><ExplorerIcon name="compass"/>{adult?"回天赋报告":"回探索星球"}</button><div><h1>{adult?`${data.account.displayName}的作品展柜`:"这些作品来源于四座大陆"}</h1></div>{adult?<button className="listen-action" aria-pressed={speech.activeKey==="works-intro"&&speech.phase==="playing"} onClick={()=>speech.toggle(`这里收藏了${data.account.displayName}的作品。`,"works-intro")}><ExplorerIcon name="headphones"/>{speech.label("works-intro","听一听")}</button>:<button className="add-work-button" onClick={()=>{setManualError("");setManualOpen(true)}}>＋ 添加作品</button>}</header><div className={`data-notice ${error?"is-error":""}`} role="status"><ExplorerIcon name="spark"/><span>{data.worksNotice}</span>{error&&<button onClick={retry}>再试一次</button>}</div>
    <main className="storybook-book"><div className="treasure-stickers">{moduleOrder.map((key,index)=>{const meta=MODULE_META[key],highlight=grouped[key].find(item=>item.isHighlight);return <button key={key} className={`treasure-sticker sticker-${index}`} onClick={()=>openSection(key)}><span className="sticker-picture"><img src={meta.scene} alt=""/><i>{index+1}</i></span><span className="sticker-caption"><i><ExplorerIcon name={iconByModule[key]}/></i><span><b>{moduleNames[key]}</b><small>{highlight?.title??grouped[key][0]?.title??"等待第一件作品"}</small></span><ExplorerIcon name="arrow"/></span></button>})}</div><p className="book-guide"><ExplorerIcon name="spark"/>点击书中贴纸查看作品列表 · 共 {data.works.length} 件</p></main>
    {!adult&&manualOpen&&<div className="work-dialog-backdrop"><section className="work-dialog" role="dialog" aria-modal="true" aria-labelledby="add-work-title"><header><div><h2 id="add-work-title">添加我的作品</h2><p>先选择所属大陆和作品类型，再写下作品内容。</p></div><button type="button" aria-label="关闭" onClick={()=>setManualOpen(false)}>×</button></header><form onSubmit={submitManualWork}><label>所属大陆<select name="module" value={manualModule} onChange={event=>setManualModule(event.target.value as WorkModule)}><option value="story">想象之洲 · 故事共创</option><option value="deep_sea">创造之洲 · 深海基地重建</option><option value="career">未来之洲 · 职业模拟器</option><option value="chat">倾听之洲 · 聊天观察</option></select></label><label>作品类型<select name="work_type" key={manualModule} defaultValue={workTypeOptions[manualModule][0].value}>{workTypeOptions[manualModule].map(option=><option key={option.value} value={option.value}>{option.label}</option>)}</select></label><label>作品名称<input name="title" required maxLength={60} placeholder="给作品起一个名字"/></label><label>作品内容或介绍<textarea name="description" maxLength={1000} placeholder="可以写下作品内容、创作过程或想说的话"/></label>{manualError&&<p className="login-error" role="alert">{manualError}</p>}<div><button type="button" onClick={()=>setManualOpen(false)}>取消</button><button className="save-work-button" disabled={manualLoading}>{manualLoading?"添加中…":"添加到作品册"}</button></div></form></section></div>}
  </section>;
}
