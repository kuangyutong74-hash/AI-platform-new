"use client";

import {useCallback,useEffect,useState} from "react";
import {createDemoCollection,normalizeCollectionResponse} from "../lib/explorer-data.mjs";
import type {ExplorerCollection} from "../lib/explorer-types";
import {CORE_API_URL} from "../config/modules";

const legacyCollection=()=>fetch(`${CORE_API_URL}/api/explorer/collection`,{credentials:"include"})
  .then(async response=>{if(!response.ok)throw new Error("暂时没有连上星球记录");return response.json();});

function collectionFromV1(account:{display_name:string;age:number;created_at?:string},artifacts:any[],sessions:any[]) {
  return {
    account,
    works:artifacts.map(artifact=>({
      id:artifact.id,module:artifact.moduleId,kind:"highlight",title:artifact.title,summary:artifact.summary,
      detail:artifact.sourceResourceId?`资源编号：${artifact.sourceResourceId}`:artifact.summary,
      occurred_at:artifact.createdAt,status:"已收藏",metric_label:"作品记录",
      metric_value:artifact.type,usage_count:1,
    })),
    milestones:sessions.map(session=>({
      id:session.id,module:session.moduleId,kind:"module_summary",title:`${session.moduleId} 的一次探索`,
      summary:`本次留下 ${session.evidenceCount} 条证据${session.artifactCount?` 和 ${session.artifactCount} 件作品`:""}。`,
      detail:`模块版本：${session.moduleVersion}`,occurred_at:session.endedAt||session.startedAt,
      status:"已完成",metric_label:"本次用时",metric_value:`${Math.max(0,Math.round((session.activeSeconds||0)/60))} 分钟`,
      usage_count:1,duration_seconds:session.activeSeconds||0,
    })),
  };
}

async function readCollectionV1(account:{display_name:string;age:number;created_at?:string}) {
  const [artifactsResponse,timelineResponse]=await Promise.all([
    fetch(`${CORE_API_URL}/api/v1/artifacts`,{credentials:"include"}),
    fetch(`${CORE_API_URL}/api/v1/timeline`,{credentials:"include"}),
  ]);
  if(!artifactsResponse.ok||!timelineResponse.ok)throw new Error("V1 星球记录暂不可用");
  const [artifacts,timeline]=await Promise.all([artifactsResponse.json(),timelineResponse.json()]);
  if(!artifacts.artifacts?.length&&!timeline.sessions?.length)throw new Error("V1 星球记录为空");
  return collectionFromV1(account,artifacts.artifacts||[],timeline.sessions||[]);
}

export default function useExplorerCollection(account:{display_name:string;age:number;created_at?:string}) {
  const [data,setData]=useState<ExplorerCollection|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [attempt,setAttempt]=useState(0);
  const retry=useCallback(()=>{setLoading(true);setError("");setAttempt(value=>value+1)},[]);
  useEffect(()=>{
    const controller=new AbortController();
    readCollectionV1({display_name:account.display_name,age:account.age,created_at:account.created_at})
      .catch(()=>legacyCollection())
      .then(payload=>setData(normalizeCollectionResponse(payload)))
      .catch(cause=>{
        if(controller.signal.aborted)return;
        const fallback=createDemoCollection({displayName:account.display_name,age:account.age,createdAt:account.created_at});
        const notice="暂时没有连上真实记录，这里先展示清楚标注的示例。你可以继续浏览，稍后再试一次。";
        setData({...fallback,worksNotice:notice,timelineNotice:notice,notice});
        setError(cause instanceof Error?cause.message:"暂时没有连上星球记录");
      })
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();
  },[account.age,account.created_at,account.display_name,attempt]);
  return {data,loading,error,retry};
}
