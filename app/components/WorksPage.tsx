"use client";

import {useMemo,useState} from "react";
import ExplorerIcon from "./ExplorerIcon";
import useExplorerCollection from "../hooks/useExplorerCollection";
import {MODULE_META} from "../lib/explorer-data.mjs";
import type {ExplorerItem,ExplorerModule} from "../lib/explorer-types";

type Account={display_name:string;age:number;created_at?:string};
type NavigationView="planet"|"works"|"timeline"|"report";
type HighlightModule=Exclude<ExplorerModule,"registration">;

const moduleOrder:HighlightModule[]=["story","deep_sea","career","chat"];
const iconByModule:Record<HighlightModule,"book"|"waves"|"map"|"journal">={story:"book",deep_sea:"waves",career:"map",chat:"journal"};

function speak(text:string){
  if(!("speechSynthesis" in window))return;
  window.speechSynthesis.cancel();
  const voice=new SpeechSynthesisUtterance(text);
  voice.lang="zh-CN";voice.rate=.82;voice.pitch=1.06;
  window.speechSynthesis.speak(voice);
}

function formatDate(value:string){
  const date=new Date(value);
  if(Number.isNaN(date.valueOf())||date.valueOf()===0)return "最近一次探索";
  return new Intl.DateTimeFormat("zh-CN",{month:"long",day:"numeric"}).format(date);
}

function WorksLoading(){return <section className="personal-loading" aria-live="polite"><span className="loading-star"><ExplorerIcon name="spark" size={38}/></span><h1>正在整理你的高光奖章…</h1><p>四座大陆正在挑选最闪亮的一次。</p></section>}

export default function WorksPage({account,onNavigate}:{account:Account;onNavigate:(view:NavigationView)=>void}){
  const {data,loading,error,retry}=useExplorerCollection(account);
  const [section,setSection]=useState<HighlightModule|null>(null);
  const [selected,setSelected]=useState<ExplorerItem|null>(null);
  const [largeText,setLargeText]=useState(false);
  const grouped=useMemo(()=>Object.fromEntries(moduleOrder.map(key=>[key,data?.works.filter(item=>item.module===key)??[]])) as Record<HighlightModule,ExplorerItem[]>,[data]);
  if(loading||!data)return <WorksLoading/>;
  const goHome=()=>{setSelected(null);setSection(null);window.scrollTo({top:0,behavior:"smooth"});};
  const openSection=(key:HighlightModule)=>{setSelected(null);setSection(key);window.scrollTo({top:0,behavior:"smooth"});};
  if(selected)return <section className={`works-view works-detail tone-${selected.tone}`}>
    <div className="works-sky" aria-hidden="true"/>
    <header className="personal-page-header">
      <button className="paper-action" onClick={()=>setSelected(null)}><ExplorerIcon name="arrow"/>放回高光页</button>
      <div><span className="header-icon"><ExplorerIcon name={iconByModule[selected.module as HighlightModule]} size={27}/></span><h1>{selected.title}</h1><p>{selected.island} · {formatDate(selected.occurredAt)}</p></div>
      <button className="listen-action" onClick={()=>speak(`${selected.title}。${selected.detail}。${selected.quote}`)}><ExplorerIcon name="headphones"/>听一听</button>
    </header>
    <main className={`work-reader ${largeText?"is-large":""}`}>
      <div className="reader-scene"><img src={selected.scene} alt={`${selected.collection}透明立体书贴纸`}/><span>{selected.status}</span></div>
      <article>
        <div className="reader-toolbar"><button onClick={()=>setLargeText(value=>!value)}>字 {largeText?"小一点":"大一点"}</button><button onClick={()=>speak(`${selected.title}。${selected.detail}`)}><ExplorerIcon name="headphones" size={17}/>朗读这一页</button></div>
        <p className="reader-date">{formatDate(selected.occurredAt)} · {data.worksAreDemo?"示例高光":"我的真实高光"}</p>
        <h2>{selected.title}</h2>
        <p className="reader-body">{selected.detail}</p>
        {selected.quote&&<blockquote>“{selected.quote.replace(/[“”]/g,"")}”</blockquote>}
        <div className="highlight-metric"><span>{selected.metricLabel}</span><strong>{selected.metricValue}</strong></div>
        <div className="reader-note"><ExplorerIcon name="spark"/><p><b>为什么它会成为高光</b><span>{selected.summary}</span></p></div>
        <div className="reader-actions"><button className="gold-button" onClick={()=>onNavigate("timeline")}><ExplorerIcon name="compass"/>看看使用历程</button><button className="plain-button" onClick={()=>setSelected(null)}>再看一枚高光</button></div>
      </article>
    </main>
  </section>;
  if(section){const meta=MODULE_META[section];const items=grouped[section];return <section className={`works-view works-collection tone-${meta.tone}`}>
    <div className="works-sky" aria-hidden="true"/>
    <header className="personal-page-header">
      <button className="paper-action" onClick={goHome}><ExplorerIcon name="arrow"/>回到高光册</button>
      <div><span className="header-icon"><ExplorerIcon name={iconByModule[section]} size={27}/></span><h1>{meta.collection}</h1><p>{meta.short}，只保留最闪亮的一次。</p></div>
      <strong>{items[0]?.metricValue??"等待点亮"}<small>{data.worksAreDemo?"示例高光":"当前高光"}</small></strong>
    </header>
    <nav className="collection-tabs" aria-label="高光分类">{moduleOrder.map(key=><button key={key} className={key===section?"active":""} onClick={()=>openSection(key)} aria-current={key===section?"page":undefined}><ExplorerIcon name={iconByModule[key]}/><span>{MODULE_META[key].collection.slice(0,6)}</span></button>)}</nav>
    <main className="collection-stage">
      <div className="collection-art"><img src={meta.scene} alt={`${meta.collection}透明立体书贴纸`}/><p><ExplorerIcon name="spark"/>{items.length?"这枚立体贴纸，代表目前最值得回看的高光。":"完成探索后，高光贴纸会来到这里。"}</p></div>
      <div className="work-list">{items.length?items.map((item,index)=><button className="work-ticket" key={item.id} onClick={()=>setSelected(item)}><span className="ticket-number">{String(index+1).padStart(2,"0")}</span><span><small>{formatDate(item.occurredAt)} · {item.status}</small><b>{item.title}</b><p>{item.summary}</p><em>{item.metricLabel} · {item.metricValue}</em></span><i><ExplorerIcon name="arrow"/></i></button>):<div className="collection-empty"><ExplorerIcon name="spark" size={34}/><h2>这里正在等第一枚高光</h2><p>去{meta.island}完成一次探索，最好的一次会变成高光奖章。</p><button onClick={()=>onNavigate("planet")}>去探索星球</button></div>}</div>
    </main>
  </section>}
  return <section className="works-view works-home">
    <div className="works-sky" aria-hidden="true"/>
    <header className="works-welcome">
      <button className="back-to-planet" onClick={()=>onNavigate("planet")}><ExplorerIcon name="compass"/>回探索星球</button>
      <div><h1>{data.account.displayName}的高光收藏册</h1><p>每座大陆只留一枚奖章，记录最好、最快或最值得回看的一次。</p></div>
      <button className="listen-action" onClick={()=>speak(`欢迎来到${data.account.displayName}的高光收藏册。四枚立体贴纸，分别记录四座大陆最闪亮的一次。`)}><ExplorerIcon name="headphones"/>听一听</button>
    </header>
    <div className={`data-notice ${error?"is-error":""}`} role="status"><ExplorerIcon name="spark"/><span>{data.worksNotice}</span>{error&&<button onClick={retry}>再试一次</button>}</div>
    <main className="storybook-book">
      <div className="book-title"><h2>四枚大陆高光奖章</h2><p>立体贴纸会随着新的最好表现自动更新</p></div>
      <div className="treasure-stickers">{moduleOrder.map((key,index)=>{const meta=MODULE_META[key];const highlight=grouped[key][0];return <button key={key} className={`treasure-sticker sticker-${index}`} onClick={()=>openSection(key)} aria-label={`打开${meta.collection}`}><span className="sticker-picture"><img src={meta.scene} alt="" loading={index>1?"lazy":"eager"}/><i aria-hidden="true">{index+1}</i></span><span className="sticker-caption"><i><ExplorerIcon name={iconByModule[key]}/></i><span><b>{meta.collection}</b><small>{highlight?.metricValue??"等待第一次探索"}</small></span><ExplorerIcon name="arrow"/></span></button>})}</div>
      <p className="book-guide"><ExplorerIcon name="spark"/>点开一枚奖章，看看它为什么成为你的高光</p>
    </main>
  </section>
}
