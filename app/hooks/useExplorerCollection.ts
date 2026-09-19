"use client";

import {useCallback,useEffect,useState} from "react";
import {canonicalExplorerModule,createDemoCollection,explorerModuleName,normalizeCollectionResponse} from "../lib/explorer-data.mjs";
import type {ExplorerCollection} from "../lib/explorer-types";
import {CORE_API_URL} from "../config/modules";

type Account={display_name:string;age:number;created_at?:string};
type V1Comment={id:string;body:string;authorName:string;authorKind:string|null;createdAt:string};
type V1Artifact={id:string;sessionId?:string|null;moduleId:string;type:string;title:string;summary:string;previewResourceId?:string|null;sourceResourceId?:string|null;createdAt:string;kind?:string;workType?:string;detail?:string;highlightReason?:string;comments?:V1Comment[]};
type V1Session={id:string;moduleId:string;endedAt?:string;startedAt?:string;activeSeconds?:number;caption?:string;evidenceCount?:number;artifactCount?:number;observations?:string[]};
type V1ModuleSummary={moduleId:string;completedCount:number;firstUsedAt:string;lastUsedAt:string;activeSeconds:number;evidenceCount:number;artifactCount:number;observations?:string[];recentSessions?:V1Session[]};
type V1GrowthSignal={key:string;label:string;evidenceCount:number;moduleCount:number;modules:string[];firstSeenAt:string;lastSeenAt:string;observation:string;status:string};

const number=(value:unknown)=>Number(value)||0;
const artifactPresentation:Record<string,{status:string;metric_label:string;metric_value:string}>={
  story:{status:"故事已完成",metric_label:"作品类型",metric_value:"故事共创"},
  chat:{status:"聊天已完成",metric_label:"记录类型",metric_value:"聊天观察"},
  deep_sea:{status:"重建已完成",metric_label:"作品类型",metric_value:"深海基地重建"},
  career:{status:"体验已完成",metric_label:"作品类型",metric_value:"职业模拟"},
};
const manualWorkTypeNames:Record<string,string>={full_story:"完整故事",story_fragment:"故事片段",character_profile:"角色设定",story_illustration:"故事插画",base_design:"基地设计",mission_record:"闯关记录",solution_sketch:"方案草图",observation_note:"观察笔记",career_card:"职业体验卡",mission_plan:"任务方案",role_diary:"角色日记",career_research:"职业小调查",mood_note:"心情小记",opinion:"观点表达",conversation_inspiration:"聊天启发",life_observation:"生活观察",other:"其他创作"};

function presentationFor(artifact:V1Artifact){
  if(artifact.kind==="manual_work"){const label=manualWorkTypeNames[artifact.workType||"other"]||"其他创作";return {status:label,metric_label:"作品类型",metric_value:label};}
  const moduleId=canonicalExplorerModule(artifact.moduleId);
  return artifactPresentation[moduleId]||{status:"已收藏",metric_label:"作品类型",metric_value:artifact.type};
}

function localDateKey(value:string){const date=new Date(value);if(Number.isNaN(date.valueOf()))return "";return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,"0")}-${String(date.getDate()).padStart(2,"0")}`;}

function collectionFromV1(account:Account,artifacts:V1Artifact[],summaries:V1ModuleSummary[],sessions:V1Session[],signals:V1GrowthSignal[]){
  const normalizedSessions=sessions.map(session=>({
    id:session.id,
    module:canonicalExplorerModule(session.moduleId),
    occurred_at:session.endedAt||session.startedAt||"",
    duration_seconds:number(session.activeSeconds),
    caption:session.caption||`完成一次${explorerModuleName(session.moduleId)}探索`,
    evidence_count:number(session.evidenceCount),
    artifact_count:number(session.artifactCount),
    observations:Array.isArray(session.observations)?session.observations:[],
  })).filter(session=>session.module);
  const todayKey=localDateKey(new Date().toISOString());
  const todaySessions=normalizedSessions.filter(session=>localDateKey(session.occurred_at)===todayKey);
  const dateKeys=new Set(normalizedSessions.map(session=>localDateKey(session.occurred_at)).filter(Boolean));
  const modules=[...new Set(normalizedSessions.map(session=>session.module))];
  const orderedDates=normalizedSessions.map(session=>session.occurred_at).filter(Boolean).sort();
  return {
    account,
    works:artifacts.filter(artifact=>canonicalExplorerModule(artifact.moduleId)).map(artifact=>({
      id:artifact.id,
      module:canonicalExplorerModule(artifact.moduleId),
      kind:artifact.kind||"highlight",
      title:artifact.title,
      summary:artifact.summary,
      detail:artifact.detail||artifact.summary,
      highlight_reason:artifact.highlightReason,
      quote:"",
      occurred_at:artifact.createdAt,
      ...presentationFor(artifact),
      usage_count:1,
      is_highlight:artifact.kind!=="manual_work",
      snapshot_url:artifact.previewResourceId?`${CORE_API_URL}/api/v1/assets/snapshots/${artifact.previewResourceId}`:"",
      source_resource_id:artifact.sourceResourceId||"",
      source_session_id:artifact.sessionId||"",
      comments:artifact.comments||[],
    })),
    milestones:[
      {
        id:"v1-registration",
        module:"registration",
        kind:"registration",
        title:`${account.display_name}来到探索星球`,
        summary:"这是第一颗星，也是所有探索故事的起点。",
        detail:"从注册这一天开始，四座大陆会把每一次完成的小脚印慢慢送到这里。",
        occurred_at:account.created_at,
        status:"星光起点",
        metric_label:"加入时间",
        metric_value:"第一次出发",
        usage_count:0,
      },
      ...summaries.filter(summary=>canonicalExplorerModule(summary.moduleId)).map(summary=>({
        id:`v1-summary-${canonicalExplorerModule(summary.moduleId)}`,
        module:canonicalExplorerModule(summary.moduleId),
        kind:"module_summary",
        title:`${explorerModuleName(summary.moduleId)}的完成小结`,
        summary:`在${explorerModuleName(summary.moduleId)}共留下 ${summary.completedCount} 次探索记录。`,
        detail:`其中包含 ${summary.evidenceCount} 条证据${summary.artifactCount?` 和 ${summary.artifactCount} 件作品`:""}。`,
        occurred_at:summary.lastUsedAt,
        status:"模块已点亮",
        metric_label:"累计完成",
        metric_value:`${summary.completedCount} 次探索 · 累计 ${Math.max(0,Math.round(number(summary.activeSeconds)/60))} 分钟`,
        usage_count:summary.completedCount,
        first_used_at:summary.firstUsedAt,
        last_used_at:summary.lastUsedAt,
        duration_seconds:summary.activeSeconds||0,
        duration_coverage:1,
        evidence_count:summary.evidenceCount,
        artifact_count:summary.artifactCount,
        observations:summary.observations||[],
        recent_sessions:(summary.recentSessions||[]).map(session=>({
          id:session.id,
          occurred_at:session.endedAt||session.startedAt,
          duration_seconds:session.activeSeconds||0,
          caption:session.caption||`完成一次${explorerModuleName(summary.moduleId)}探索`,
        })),
      })),
    ],
    growth_overview:{
      sessions:normalizedSessions,
      today_sessions:todaySessions,
      today_completed_count:todaySessions.length,
      today_duration_seconds:todaySessions.reduce((sum,item)=>sum+item.duration_seconds,0),
      today_evidence_count:todaySessions.reduce((sum,item)=>sum+item.evidence_count,0),
      today_modules:[...new Set(todaySessions.map(item=>item.module))],
      total_completed_count:normalizedSessions.length,
      total_duration_seconds:normalizedSessions.reduce((sum,item)=>sum+item.duration_seconds,0),
      active_days:dateKeys.size,
      explored_module_count:modules.length,
      first_completed_at:orderedDates[0]||"",
      last_completed_at:orderedDates.at(-1)||"",
      long_term_signals:signals,
    },
  };
}

async function readCollectionV1(account:Account,signal:AbortSignal){
  const [artifactsResponse,timelineResponse]=await Promise.all([
    fetch(`${CORE_API_URL}/api/v1/artifacts`,{credentials:"include",signal}),
    fetch(`${CORE_API_URL}/api/v1/timeline`,{credentials:"include",signal}),
  ]);
  if(!artifactsResponse.ok||!timelineResponse.ok)throw new Error("暂时没有连上星球记录");
  const [artifacts,timeline]=await Promise.all([artifactsResponse.json(),timelineResponse.json()]);
  return collectionFromV1(
    account,
    artifacts.artifacts||[],
    timeline.moduleSummaries||[],
    timeline.sessions||[],
    timeline.longTermSignals||[],
  );
}

export default function useExplorerCollection(account:Account){
  const [data,setData]=useState<ExplorerCollection|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [attempt,setAttempt]=useState(0);
  const retry=useCallback(()=>{setLoading(true);setError("");setAttempt(value=>value+1)},[]);
  const refresh=useCallback(()=>setAttempt(value=>value+1),[]);
  useEffect(()=>{
    const controller=new AbortController();
    readCollectionV1(account,controller.signal)
      .then(payload=>setData(normalizeCollectionResponse(payload)))
      .catch(cause=>{
        if(controller.signal.aborted)return;
        const fallback=createDemoCollection({displayName:account.display_name,age:account.age,createdAt:account.created_at});
        const notice="暂时没有连上真实记录，这里先展示清楚标注的示例。你可以继续浏览，稍后再试一次。";
        setData({...fallback,worksNotice:notice,timelineNotice:notice,notice});
        setError(cause instanceof Error?cause.message:"暂时没有连上星球记录");
      })
      .finally(()=>{if(!controller.signal.aborted)setLoading(false)});
    return()=>controller.abort();
  },[account.display_name,account.age,account.created_at,attempt]);
  return {data,loading,error,retry,refresh};
}
