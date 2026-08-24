"use client";

import {useCallback,useEffect,useState} from "react";
import {createDemoCollection,normalizeCollectionResponse} from "../lib/explorer-data.mjs";
import type {ExplorerCollection} from "../lib/explorer-types";

const CORE_URL="http://localhost:8020";

export default function useExplorerCollection(account:{display_name:string;age:number;created_at?:string}) {
  const [data,setData]=useState<ExplorerCollection|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [attempt,setAttempt]=useState(0);
  const retry=useCallback(()=>{setLoading(true);setError("");setAttempt(value=>value+1)},[]);
  useEffect(()=>{
    const controller=new AbortController();
    fetch(`${CORE_URL}/api/explorer/collection`,{credentials:"include",signal:controller.signal})
      .then(async response=>{if(!response.ok)throw new Error("暂时没有连上星球记录");return response.json();})
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
