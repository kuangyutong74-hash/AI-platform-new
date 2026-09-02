import type { CoreEvidenceRecord } from "../api/core";
import type { DeepSeaPipelineScene, Moment, MomentSceneData } from "./mockReport";

const moduleMeta:Record<string,{kind:Moment["kind"];name:string}> = {
  story:{kind:"story",name:"故事共创"}, deep_sea:{kind:"base",name:"深海基地重建"},
  chat:{kind:"chat",name:"聊天观察"}, career:{kind:"career",name:"职业模拟器"},
};
const eventTitles:Record<string,string> = {
  "story.contribution-completed.v1":"故事创作台", "chat.observation-shared.v1":"聊天分享",
  "deep-sea.spatial-task-completed.v1":"能源管线", "deep-sea.session-completed.v1":"完整重建",
  "career.task-completed.v1":"职业任务回顾",
};
const numberValue=(value:unknown,fallback:number)=>typeof value==="number"&&Number.isFinite(value)?value:fallback;
const stringValue=(value:unknown,fallback="")=>typeof value==="string"?value.trim():fallback;

function firstString(payload:Record<string,unknown>,keys:string[]):string|undefined {
  const value=keys.map(key=>payload[key]).find(candidate=>typeof candidate==="string"&&candidate.trim());
  return typeof value==="string"?value.trim():undefined;
}
function quoteFrom(event:CoreEvidenceRecord):string|undefined {
  return firstString(event.payload,["childWords","childEnding","quote","child_words","child_ending"])?.slice(0,72);
}
function imageFrom(event:CoreEvidenceRecord):string|undefined {
  if(event.previewUrl)return event.previewUrl;
  const value=firstString(event.payload,["snapshotUrl","imageUrl","snapshot_url","image_url"]);
  return value&&/^https?:\/\//.test(value)?value:undefined;
}
function pipelineSceneFrom(event:CoreEvidenceRecord):DeepSeaPipelineScene|undefined {
  if(event.moduleId!=="deep_sea"||event.eventType!=="deep-sea.spatial-task-completed.v1")return undefined;
  const raw=event.payload,layout=raw.pipeLayout??raw.pipe_layout;
  const pipes=Array.isArray(layout)?layout.filter(item=>item&&typeof item==="object").map(item=>{const value=item as Record<string,unknown>;return {row:numberValue(value.row,0),col:numberValue(value.col,0),def:stringValue(value.def,"─"),rot:numberValue(value.rot,0),energized:Boolean(value.energized)}}):[];
  if(!pipes.length)return undefined;
  const obstacleLayout=raw.obstacleLayout??raw.obstacle_layout;
  const obstacles=Array.isArray(obstacleLayout)?obstacleLayout.filter(item=>item&&typeof item==="object").map(item=>{const value=item as Record<string,unknown>;return {row:numberValue(value.row,0),col:numberValue(value.col,0),kind:stringValue(value.kind,"rock")}}):[];
  const start=((raw.startCell??raw.start_cell)??{}) as Record<string,unknown>,end=((raw.endCell??raw.end_cell)??{}) as Record<string,unknown>;
  const attempts=raw.checkAttempts??raw.check_attempts;
  return {type:"deep_sea_pipeline",version:numberValue(raw.rendererVersion??raw.renderer_version,1),rows:numberValue(raw.gridRows??raw.grid_rows,8),cols:numberValue(raw.gridCols??raw.grid_cols,10),pipes,obstacles,start:{row:numberValue(start.row,0),col:numberValue(start.col,0)},end:{row:numberValue(end.row,7),col:numberValue(end.col,9)},connected:raw.connected!==false,rotateCount:numberValue(raw.adjustmentCount??raw.rotate_count,0),checkAttempts:typeof attempts==="number"?attempts:null};
}
function sceneFrom(event:CoreEvidenceRecord):MomentSceneData|undefined {
  const pipeline=pipelineSceneFrom(event);if(pipeline)return pipeline;
  const raw=event.payload;
  if(event.moduleId==="story")return {type:"story",title:stringValue(raw.storyTitle??event.artifactTitle??raw.title,"我的共创故事"),words:stringValue(event.sessionSummary?.childEnding??raw.childWords??raw.child_words),turns:numberValue(raw.contributionCount??raw.turn_number,0),mode:stringValue(event.sessionSummary?.completionMode??raw.completionMode??raw.completion_mode,"director")};
  if(event.moduleId==="chat")return {type:"chat",topic:stringValue(raw.topicKey??raw.topic,"最近的发现"),words:stringValue(event.sessionSummary?.childWords??raw.childWords??raw.child_words),turns:numberValue(raw.turnCount??raw.turn_count,0)};
  if(event.moduleId==="career")return {type:"career",career:stringValue(raw.taskKey??raw.career_name,"职业体验"),completed:numberValue(raw.completedStages??raw.completed_stages,1),stages:numberValue(raw.stageCount??raw.stage_count,3),adjustments:numberValue(raw.adjustmentCount??raw.adjustment_count,0),retries:numberValue(raw.attemptCount??raw.retry_count,0),hints:numberValue(raw.hintCount??raw.hint_count,0)};
  return undefined;
}
export function momentFromEvidence(event:CoreEvidenceRecord):Moment {
  const meta=moduleMeta[event.moduleId]||{kind:"career" as const,name:event.moduleId};
  return {id:`M-${event.id.slice(-6).toUpperCase()}`,kind:meta.kind,title:`${meta.name} · ${eventTitles[event.eventType]||"认真尝试的这一刻"}`,caption:event.behaviorSummary,quote:quoteFrom(event),source:meta.name,time:event.occurredAt.replace("T"," ").slice(0,16),evidenceId:event.id,imageUrl:imageFrom(event),sceneData:sceneFrom(event)};
}
export function momentsForTalent(events:CoreEvidenceRecord[],talentKey:string):Moment[] {
  return events.filter(event=>event.reportDimensions.includes(talentKey)).sort((a,b)=>a.evidenceLevel===b.evidenceLevel?Date.parse(b.occurredAt)-Date.parse(a.occurredAt):a.evidenceLevel==="strong"?-1:1).slice(0,2).map(momentFromEvidence);
}
