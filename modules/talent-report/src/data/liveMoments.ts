import type { CoreEvidence } from "../api/core";
import type { DeepSeaPipelineScene, Moment, MomentSceneData } from "./mockReport";

const moduleMeta:Record<string,{kind:Moment["kind"];name:string}> = {
  story: { kind:"story", name:"故事共创" },
  deep_sea: { kind:"base", name:"深海基地重建" },
  chat: { kind:"chat", name:"聊天观察" },
  career: { kind:"career", name:"职业模拟器" },
};

const eventTitles:Record<string,string> = {
  story_completion:"我的故事结尾",
  story_contribution:"故事创作台",
  story_revision:"故事修改台",
  narrative_evidence:"聊天分享",
  ecology_strategy:"生态配对",
  spatial_solution:"能源管线",
  mediation_response:"小队协商",
  workday_process_summary:"职业任务回顾",
  decision_revision:"方案调整",
};

function quoteFrom(event:CoreEvidence):string|undefined {
  const candidates = [event.raw_evidence.child_text,event.raw_evidence.child_ending,event.raw_evidence.quote,event.context.child_text];
  const quote = candidates.find(value=>typeof value==="string"&&value.trim()) as string|undefined;
  return quote?.trim().slice(0,72);
}

function imageFrom(event:CoreEvidence):string|undefined {
  const values=[event.context.snapshot_url,event.context.image_url,event.context.imageUrl,event.raw_evidence.image_url,event.raw_evidence.imageUrl];
  return values.find(value=>typeof value==="string"&&/^https?:\/\//.test(value)) as string|undefined;
}

const numberValue=(value:unknown,fallback:number)=>typeof value==="number"&&Number.isFinite(value)?value:fallback;
function pipelineSceneFrom(event:CoreEvidence):DeepSeaPipelineScene|undefined {
  if(event.module!=="deep_sea"||event.event_type!=="spatial_solution")return undefined;
  const raw=event.raw_evidence;
  const pipes=Array.isArray(raw.pipe_layout)?raw.pipe_layout.filter(item=>item&&typeof item==="object").map(item=>{const value=item as Record<string,unknown>;return {row:numberValue(value.row,0),col:numberValue(value.col,0),def:typeof value.def==="string"?value.def:"─",rot:numberValue(value.rot,0),energized:Boolean(value.energized)}}):[];
  if(!pipes.length)return undefined;
  const obstacles=Array.isArray(raw.obstacle_layout)?raw.obstacle_layout.filter(item=>item&&typeof item==="object").map(item=>{const value=item as Record<string,unknown>;return {row:numberValue(value.row,0),col:numberValue(value.col,0),kind:typeof value.kind==="string"?value.kind:"rock"}}):[];
  const start=(raw.start_cell&&typeof raw.start_cell==="object"?raw.start_cell:{}) as Record<string,unknown>;
  const end=(raw.end_cell&&typeof raw.end_cell==="object"?raw.end_cell:{}) as Record<string,unknown>;
  return {type:"deep_sea_pipeline",version:numberValue(raw.renderer_version,1),rows:numberValue(raw.grid_rows,8),cols:numberValue(raw.grid_cols,10),pipes,obstacles,start:{row:numberValue(start.row,0),col:numberValue(start.col,0)},end:{row:numberValue(end.row,7),col:numberValue(end.col,9)},connected:raw.connected!==false,rotateCount:numberValue(raw.rotate_count,0),checkAttempts:typeof raw.check_attempts==="number"?raw.check_attempts:null};
}

const stringValue=(value:unknown,fallback="")=>typeof value==="string"?value.trim():fallback;
function sceneFrom(event:CoreEvidence):MomentSceneData|undefined {
  const pipeline=pipelineSceneFrom(event);if(pipeline)return pipeline;
  const raw=event.raw_evidence;
  if(event.module==="deep_sea"&&event.event_type==="ecology_strategy"){
    const details=Array.isArray(raw.pair_details)?raw.pair_details.filter(item=>item&&typeof item==="object").map(item=>{const value=item as Record<string,unknown>;return {label:stringValue(value.label),done:Boolean(value.done)}}):[];
    const pairCount=numberValue(raw.successful_pairs,0);const pairs=details.length?details:Array.from({length:Math.max(1,pairCount)},(_,index)=>({label:`生态组合 ${index+1}`,done:true}));
    return {type:"deep_sea_ecology",pairs,adjustments:numberValue(raw.meaningful_adjustments,0),checks:typeof raw.check_attempts==="number"?raw.check_attempts:null};
  }
  if(event.module==="deep_sea"&&event.event_type==="mediation_response")return {type:"deep_sea_mediation",harmony:numberValue(raw.harmony_final,raw.harmony_band==="high"?88:68),rounds:numberValue(raw.rounds_used,0),solution:stringValue(raw.solution_summary)};
  if(event.module==="story")return {type:"story",title:stringValue(raw.title,"我的共创故事"),words:stringValue(raw.child_words),turns:numberValue(raw.turn_number,0),mode:stringValue(raw.completion_mode,"director")};
  if(event.module==="chat")return {type:"chat",topic:stringValue(raw.topic,"最近的发现"),words:stringValue(raw.child_words),turns:numberValue(raw.turn_count,0)};
  if(event.module==="career")return {type:"career",career:stringValue(raw.career_name,"职业体验"),completed:numberValue(raw.completed_stages,0),stages:numberValue(raw.stage_count,3),adjustments:numberValue(raw.adjustment_count,0),retries:numberValue(raw.retry_count,0),hints:numberValue(raw.hint_count,0)};
  return undefined;
}

export function momentFromEvidence(event:CoreEvidence):Moment {
  const meta=moduleMeta[event.module]||{kind:"career" as const,name:event.module};
  const title=eventTitles[event.event_type]||"认真尝试的这一刻";
  return {
    id:`M-${event.id.slice(-6).toUpperCase()}`,
    kind:meta.kind,
    title:`${meta.name} · ${title}`,
    caption:event.behavior_summary,
    quote:quoteFrom(event),
    source:meta.name,
    time:event.occurred_at.replace("T"," ").slice(0,16),
    evidenceId:event.id,
    imageUrl:imageFrom(event),
    sceneData:sceneFrom(event),
  };
}

export function momentsForTalent(events:CoreEvidence[],talentKey:string):Moment[] {
  return events
    .filter(event=>event.intelligence_candidates.map(key=>key==="logical_mathematical"?"logical":key).includes(talentKey))
    .sort((a,b)=>(a.evidence_level===b.evidence_level?Date.parse(b.occurred_at)-Date.parse(a.occurred_at):a.evidence_level==="strong"?-1:1))
    .slice(0,2)
    .map(momentFromEvidence);
}
