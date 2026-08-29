import type { CoreEvidenceRecord } from "../api/core";
import type { Moment } from "./mockReport";

const moduleMeta:Record<string,{kind:Moment["kind"];name:string}>={story:{kind:"story",name:"故事共创"},deep_sea:{kind:"base",name:"深海基地重建"},chat:{kind:"chat",name:"聊天观察"},career:{kind:"career",name:"职业模拟器"}};
const eventTitles:Record<string,string>={"story.contribution-completed.v1":"故事创作台","chat.observation-shared.v1":"聊天分享","deep-sea.spatial-task-completed.v1":"深海任务","deep-sea.session-completed.v1":"完整重建","career.task-completed.v1":"职业任务回顾"};
function quoteFrom(event:CoreEvidenceRecord){const payload=event.payload||{};return [payload.childWords,payload.childEnding,payload.quote].find(value=>typeof value==="string"&&value.trim()) as string|undefined}
export function momentFromEvidence(event:CoreEvidenceRecord):Moment{const meta=moduleMeta[event.moduleId]||{kind:"career" as const,name:event.moduleId};return {id:`M-${event.id.slice(-6).toUpperCase()}`,kind:meta.kind,title:`${meta.name} · ${eventTitles[event.eventType]||"认真尝试的这一刻"}`,caption:event.behaviorSummary,quote:quoteFrom(event)?.slice(0,72),source:meta.name,time:event.occurredAt.replace("T"," ").slice(0,16),evidenceId:event.id}}
export function momentsForTalent(events:CoreEvidenceRecord[],talentKey:string):Moment[]{return events.filter(event=>event.reportDimensions.includes(talentKey)).sort((a,b)=>a.evidenceLevel===b.evidenceLevel?Date.parse(b.occurredAt)-Date.parse(a.occurredAt):a.evidenceLevel==="strong"?-1:1).slice(0,2).map(momentFromEvidence)}
