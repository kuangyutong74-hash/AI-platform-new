import type { CoreEvidence } from "../api/core";
import type { Moment } from "./mockReport";

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
  };
}

export function momentsForTalent(events:CoreEvidence[],talentKey:string):Moment[] {
  return events
    .filter(event=>event.intelligence_candidates.map(key=>key==="logical_mathematical"?"logical":key).includes(talentKey))
    .sort((a,b)=>(a.evidence_level===b.evidence_level?Date.parse(b.occurred_at)-Date.parse(a.occurred_at):a.evidence_level==="strong"?-1:1))
    .slice(0,2)
    .map(momentFromEvidence);
}
