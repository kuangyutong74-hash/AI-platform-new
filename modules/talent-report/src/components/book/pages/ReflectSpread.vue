<script setup lang="ts">
import {computed, ref} from "vue";
import {submitParentFeedback, type GeneratedReport, type ReflectionAnswer, type ReflectionQuestion, type ReflectionQuestions} from "../../../api/core";

const props=defineProps<{side:"left"|"right";questions?:ReflectionQuestions;report?:GeneratedReport}>();
const emit=defineEmits<{complete:[report?:GeneratedReport];skip:[]}>();
const answers=ref<Record<string,ReflectionAnswer>>({});
const submitting=ref(false),error=ref(""),transition=ref("");
const cacheKey=computed(()=>`ai-bole-reflection-${props.report?.report_id||"preview"}`);
const completed=computed(()=>Boolean(props.report?.feedback_completed));

function fallbackQuestions():ReflectionQuestions{
  if(!props.report)return {lead_note:"",dimension_questions:[],global_questions:[]};
  const dimensions=Array.isArray(props.report.dimensions)?props.report.dimensions:[];
  const dimension=dimensions.find(item=>item.evidence_refs?.length)||dimensions[0];
  const evidenceRef=dimension?.evidence_refs?.[0];
  const explanation=props.report.evidence_explanations?.find(item=>item.evidence_ref===evidenceRef);
  const dimensionQuestions:ReflectionQuestion[]=dimension?[{
    id:"d1",key:dimension.key,evidence_ref:evidenceRef,module:"report",
    evidence_brief:explanation?.summary||dimension.analysis?.slice(0,36)||"报告中已经留下了一次真实观察",
    lead:"一起看看——",question:"在家里也见过类似的表现吗？",
    options:["经常见到","偶尔见到","很少见到","没注意过"],allow_text:true,placeholder:"可以补充一个小例子",
  }]:[];
  return {
    lead_note:"您的回答会和魔法书里的观察放在一起，形成更贴近孩子的建议。",
    dimension_questions:dimensionQuestions,
    global_questions:[
      {id:"g1",category:"家庭陪伴",lead:"关于陪伴——",question:"平时谁陪孩子探索得更多？",options:["爸爸妈妈","祖辈家人","大家轮流","其他陪伴"],allow_text:true,placeholder:"最常一起做什么？"},
      {id:"g2",category:"期待",lead:"关于期待——",question:"最希望孩子在哪方面多尝试？",options:["表达想法","动手解决","理解伙伴","认识自己"],allow_text:true,placeholder:"写下一件期待的小事"},
      {id:"g3",category:"在意",lead:"最近在意——",question:"最近最想多了解孩子什么？",options:["兴趣变化","遇难反应","合作方式","还没想好"],allow_text:true,placeholder:"可以写下最近的观察"},
    ],
  };
}
const effectiveQuestions=computed(()=>{
  const fallback=fallbackQuestions(),provided=props.questions;
  return {
    lead_note:provided?.lead_note||fallback.lead_note,
    dimension_questions:provided?.dimension_questions?.length?provided.dimension_questions:fallback.dimension_questions,
    global_questions:provided?.global_questions?.length?provided.global_questions:fallback.global_questions,
  };
});
const visibleQuestions=computed(()=>props.side==="left"?effectiveQuestions.value.dimension_questions:effectiveQuestions.value.global_questions);

function answerFor(question:ReflectionQuestion){return answers.value[question.id]||{id:question.id,selected:"",text:""}}
function persistDraft(){localStorage.setItem(`${cacheKey.value}-draft`,JSON.stringify(answers.value))}
function select(question:ReflectionQuestion,value:string){answers.value[question.id]={...answerFor(question),selected:value};persistDraft()}
function write(question:ReflectionQuestion,value:string){answers.value[question.id]={...answerFor(question),text:value};persistDraft()}
function writeFromEvent(question:ReflectionQuestion,event:Event){write(question,(event.target as HTMLTextAreaElement).value)}
function skip(){emit("skip")}
async function submit(){
  if(!props.report?.report_id){error.value="这份报告还没有保存好，请稍后再试。";return}
  const dimensionQuestions=effectiveQuestions.value.dimension_questions;
  if(!dimensionQuestions.length){skip();return}
  submitting.value=true;error.value="";
  try{
    let latest=props.report;
    const allQuestions=[...effectiveQuestions.value.dimension_questions,...effectiveQuestions.value.global_questions];
    const draft=localStorage.getItem(`${cacheKey.value}-draft`);
    const merged=draft?JSON.parse(draft) as Record<string,ReflectionAnswer>:answers.value;
    const allAnswers=allQuestions.map(question=>merged[question.id]||answerFor(question));
    for(const question of dimensionQuestions){
      const result=await submitParentFeedback(props.report.report_id!,question.key!,allQuestions,allAnswers);
      latest=result.report;transition.value=result.suggestion.transition_note;
    }
    localStorage.removeItem(`${cacheKey.value}-draft`);
    window.setTimeout(()=>emit("complete",latest),700);
  }catch(cause){error.value=cause instanceof Error?cause.message:"专属建议暂时没有写好，请稍后再试。"}
  finally{submitting.value=false}
}
</script>

<template>
  <div class="reflect-page" :class="`reflect-${side}`">
    <p class="page-kicker">STAR LETTER · 08</p>
    <template v-if="completed">
      <h2>星章已经收好这封信</h2>
      <div class="reflect-complete"><span aria-hidden="true">✦</span><p>{{transition||`感谢您的补充，属于孩子的建议已经写进下一页。`}}</p></div>
      <button v-if="side==='right'" class="envelope-button" @click="emit('complete',report)">翻到专属建议</button>
    </template>
    <template v-else>
      <h2>{{side==='left'?'也想听听您眼中的孩子':'再写下三件小事'}}</h2>
      <p v-if="side==='left'" class="lead-note">{{effectiveQuestions.lead_note||'您的回答会和魔法书里的观察放在一起。'}}</p>
      <p v-else class="star-letter-intro">没有标准答案，只写您平时真实看到的样子。</p>
      <div v-if="visibleQuestions.length" class="reflection-questions">
        <article v-for="(question,index) in visibleQuestions" :key="question.id" class="q-card" :data-module="question.module">
          <i>{{index+1}}</i><h3>{{question.lead}}</h3>
          <span v-if="question.evidence_brief" class="evidence-chip"><b>✦</b>{{question.evidence_brief}}</span>
          <p>{{question.question}}</p>
          <div class="options" role="group" :aria-label="question.question">
            <button v-for="option in question.options" :key="option" type="button" class="option" :class="{selected:answerFor(question).selected===option}" :aria-pressed="answerFor(question).selected===option" @click="select(question,option)">{{option}}</button>
          </div>
          <textarea v-if="question.allow_text" class="q-extra" rows="2" maxlength="120" :placeholder="question.placeholder" :value="answerFor(question).text" @input="writeFromEvent(question,$event)"/>
        </article>
      </div>
      <div v-else class="reflect-empty"><p>这一阶段还没有足够具体的维度问题。</p><span>可以继续探索，也可以直接阅读通用建议。</span></div>
      <p v-if="error" class="reflect-error" role="alert">{{error}}</p>
      <p v-if="transition" class="result-note show" role="status">{{transition}}</p>
      <div v-if="side==='right'" class="sheet-actions">
        <button class="paper-button" type="button" :disabled="submitting" @click="skip">这次先跳过</button>
        <button class="envelope-button" type="button" :disabled="submitting" @click="submit">{{submitting?'星章正在写…':'生成专属建议'}}</button>
      </div>
    </template>
  </div>
</template>
