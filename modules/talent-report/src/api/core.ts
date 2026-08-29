const CORE_URL = import.meta.env.VITE_CORE_API_URL || "http://localhost:8020";
export type CoreAccount = { id:string; username:string; display_name:string; age?:number; created_at:string };
export type TalentEligibility = { key:string; name:string; eligible:boolean; strong_count:number; reference_count:number; source_modules:string[]; recent_evidence_id:string|null };
export type CoreEvidence = { id:string; module:string; event_type:string; occurred_at:string; evidence_level:"strong"|"reference"; intelligence_candidates:string[]; behavior_summary:string; raw_evidence:Record<string,unknown>; context:Record<string,unknown> };
export type ReportDimension = { key:string; name:string; status:string; evidence_refs:string[]; analysis:string; adult_observation:string; child_story:string };
export type EvidenceExplanation = { evidence_ref:string|null;title:string;summary:string;details:string[] };
export type GeneratedReport = { generated_at:string; rule:string; dimensions:ReportDimension[]; cross_insights:{text:string;evidence_refs:string[]}[]; evidence_explanations:EvidenceExplanation[]; recommendations:{family:string|string[];teacher:string|string[]} };
async function coreFetch<T>(path:string):Promise<T|null>{try{const response=await fetch(`${CORE_URL}${path}`,{credentials:"include"});if(!response.ok)return null;return await response.json() as T}catch{return null}}
export async function getAccount(){return coreFetch<{account:CoreAccount}>("/api/account/me")}
export async function getTalentEligibility(){return coreFetch<{account_id:string;talents:TalentEligibility[]}>("/api/explorer/talents")}
export async function getEvidence(){return coreFetch<{account:CoreAccount;events:CoreEvidence[]}>("/api/evidence/events?limit=500")}
export async function generateReport(_childName:string,_events:CoreEvidence[]):Promise<GeneratedReport|null>{try{const latest=await coreFetch<{report:GeneratedReport}>("/api/v1/reports/latest-published");if(latest?.report)return latest.report;const response=await fetch(`${CORE_URL}/api/v1/reports`,{method:"POST",credentials:"include"});if(!response.ok)return null;return (await response.json() as {report:GeneratedReport}).report}catch{return null}}
