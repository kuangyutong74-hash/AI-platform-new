const CORE_URL = import.meta.env.VITE_CORE_API_URL || "http://localhost:8020";
export type CoreAccount = { id:string; username:string; display_name:string; age?:number; created_at:string };
export type TalentEligibility = { key:string; name:string; eligible:boolean; strongCount:number; referenceCount:number; sourceModules:string[]; recentEvidenceRecordId:string|null };
export type CoreEvidenceRecord = { id:string; sourceEventId:string; sessionId:string; moduleId:string; moduleVersion:string; eventType:string; occurredAt:string; evidenceLevel:"strong"|"reference"; constructs:string[]; reportDimensions:string[]; behaviorSummary:string; payload:Record<string,unknown> };
export type ReportDimension = { key:string; name:string; status:string; evidence_refs:string[]; analysis:string; adult_observation:string; child_story:string };
export type EvidenceExplanation = { evidence_ref:string|null;title:string;summary:string;details:string[] };
export type GeneratedReport = { generated_at:string; rule:string; dimensions:ReportDimension[]; cross_insights:{text:string;evidence_refs:string[]}[]; evidence_explanations:EvidenceExplanation[]; recommendations:{family:string|string[];teacher:string|string[]} };
async function coreFetch<T>(path:string):Promise<T|null>{try{const response=await fetch(`${CORE_URL}${path}`,{credentials:"include"});if(!response.ok)return null;return await response.json() as T}catch{return null}}
export async function getAccount(){const payload=await coreFetch<{account:CoreAccount;selected_student?:CoreAccount|null}>("/api/account/me");return payload?{account:payload.selected_student||payload.account}:null}
export async function getTalentEligibility(){return coreFetch<{rule:string;talents:TalentEligibility[]}>("/api/v1/talents")}
export async function getEvidenceRecords(){return coreFetch<{records:CoreEvidenceRecord[]}>("/api/v1/evidence-records?limit=500")}
export async function generateReport():Promise<GeneratedReport|null>{try{const latest=await coreFetch<{report:GeneratedReport}>("/api/v1/reports/latest-published");if(latest?.report)return latest.report;const response=await fetch(`${CORE_URL}/api/v1/reports`,{method:"POST",credentials:"include"});if(!response.ok)return null;return (await response.json() as {report:GeneratedReport}).report}catch{return null}}
