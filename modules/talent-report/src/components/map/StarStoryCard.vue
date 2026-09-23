<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import type { Talent } from "../../data/mockReport";
import { mapCopy, stickerByKey, type StarReflection, type StarReflectionChoice } from "../../data/treasureMap";
type SpeechEvent={results:ArrayLike<{0:{transcript:string}}>};
type SpeechErrorEvent={error:string};
type SpeechEngine={lang:string;interimResults:boolean;continuous:boolean;start:()=>void;stop:()=>void;onresult:((event:SpeechEvent)=>void)|null;onerror:((event:SpeechErrorEvent)=>void)|null;onend:(()=>void)|null};
type SpeechConstructor=new()=>SpeechEngine;
const props=defineProps<{talent:Talent;story?:string;loading:boolean;failed:boolean;order:number;canCollect:boolean;reflection?:StarReflection}>();
const emit=defineEmits<{close:[];collect:[];visit:[url:string];openWorks:[];saveReflection:[value:StarReflection]}>();
const choice=ref<StarReflectionChoice|"">(""),reason=ref(""),listening=ref(false),speechMessage=ref(""),saved=ref(false);
let recognition:SpeechEngine|undefined;
const speechScope=()=>window as unknown as {SpeechRecognition?:SpeechConstructor;webkitSpeechRecognition?:SpeechConstructor};
const speechSupported=computed(()=>Boolean(speechScope().SpeechRecognition||speechScope().webkitSpeechRecognition));
const evidenceLines=computed(()=>{
  const seen=new Set<string>();
  return props.talent.evidence.filter(item=>{const key=item.behavior.replace(/\s+/g,"").replace(/[。；]/g,"");if(!key||seen.has(key))return false;seen.add(key);return true}).slice(0,3);
});
const starState=computed(()=>evidenceLines.value.length>=3?"线索丰富":evidenceLines.value.length>=2?"正在闪亮":"发现中");
watch(()=>[props.talent.key,props.reflection] as const,()=>{choice.value=props.reflection?.choice||"";reason.value=props.reflection?.reason||"";saved.value=Boolean(props.reflection);speechMessage.value=""},{immediate:true});
watch([choice,reason],()=>{saved.value=false});
onBeforeUnmount(()=>recognition?.stop());
function toggleSpeech(){if(listening.value){recognition?.stop();return}const Recognition=speechScope().SpeechRecognition||speechScope().webkitSpeechRecognition;if(!Recognition){speechMessage.value="这个浏览器暂不支持语音输入，可以用键盘写下来。";return}recognition=new Recognition();recognition.lang="zh-CN";recognition.interimResults=false;recognition.continuous=false;recognition.onresult=event=>{const text=event.results[0]?.[0]?.transcript?.trim();if(text)reason.value=[reason.value.trim(),text].filter(Boolean).join(" ");speechMessage.value="已经把你说的话写下来了。"};recognition.onerror=event=>{
  const kind=event?.error||"";
  if(kind==="not-allowed"||kind==="service-not-allowed")speechMessage.value="麦克风权限没有打开。可以在浏览器地址栏旁边允许麦克风，再试一次。";
  else if(kind==="no-speech")speechMessage.value="刚才没有听到声音，靠近一点再说一次吧。";
  else if(kind==="audio-capture")speechMessage.value="没有找到麦克风，检查一下设备连接。";
  else if(kind==="network")speechMessage.value="网络不太顺畅，稍等一下再试。";
  else speechMessage.value="这次没有听清，可以再说一次。";
};
recognition.onend=()=>{listening.value=false};listening.value=true;speechMessage.value="正在听，请说出你的理由……";try{recognition.start()}catch{listening.value=false;speechMessage.value="麦克风没有准备好，请再试一次。"}}
function save(){if(!choice.value)return;emit("saveReflection",{choice:choice.value,reason:reason.value.trim(),updatedAt:new Date().toISOString()});saved.value=true}
</script>
<template><div class="story-card-backdrop" @click.self="$emit('close')"><article class="star-story-card" role="dialog" aria-modal="true" :aria-labelledby="`story-${talent.key}`"><header><div><p>{{mapCopy.source(talent.continent)}}</p><small>{{starState}}<template v-if="order>0"> · {{mapCopy.order(order)}}</template></small></div><img :src="stickerByKey[talent.key]" alt=""/></header><h2 :id="`story-${talent.key}`">{{talent.childName}}</h2><p class="story-card-label">这颗星在告诉你什么</p><blockquote :class="{'is-empty':!story}">{{story||(loading?'智能体正在阅读这次游戏记录，马上就能写好这颗星的专属发现……':failed?'智能体这次没有连接成功，请稍后重新打开藏宝图。':'这次体验已经完成，但保存的记录还不足以描述这颗星。')}}</blockquote><section class="star-evidence" aria-label="这颗星的真实线索"><h3>这颗星从这些体验里慢慢亮起来</h3><ul><li v-for="item in evidenceLines" :key="item.id"><b>{{item.source}} · {{item.time}}</b><span>{{item.behavior}}</span></li></ul></section><section v-if="!canCollect" class="star-reflection" aria-labelledby="star-reflection-title"><h3 id="star-reflection-title">这颗星像你吗？</h3><p>没有标准答案，选最接近你现在感觉的就好。</p><div class="reflection-choices" role="radiogroup" aria-label="这颗星像不像我"><button type="button" role="radio" :aria-checked="choice==='like_me'" :class="{selected:choice==='like_me'}" @click="choice='like_me'">像我</button><button type="button" role="radio" :aria-checked="choice==='not_me'" :class="{selected:choice==='not_me'}" @click="choice='not_me'">不像我</button><button type="button" role="radio" :aria-checked="choice==='unsure'" :class="{selected:choice==='unsure'}" @click="choice='unsure'">不确定</button></div><label :for="`star-reason-${talent.key}`">愿意说说为什么吗？<span>（可以不填）</span></label><div class="reflection-input"><textarea :id="`star-reason-${talent.key}`" v-model="reason" maxlength="300" rows="2" placeholder="比如：我也喜欢这样做……"/><button type="button" class="speech-input" :class="{listening}" :aria-pressed="listening" :disabled="!speechSupported" @click="toggleSpeech"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3M9 21h6"/></svg>{{listening?'停止':'语音输入'}}</button></div><small class="speech-status" aria-live="polite">{{speechMessage||(!speechSupported?'当前浏览器不支持语音输入，可以直接打字。':'点“语音输入”，说完后会自动变成文字。')}}</small><button type="button" class="reflection-save" :disabled="!choice" @click="save">{{saved?'已保存 ✓':'保存我的想法'}}</button></section><footer><button class="story-visit" @click="$emit('openWorks')">看看相关作品</button><button class="story-visit" @click="$emit('visit',talent.moduleUrl)">{{mapCopy.visit(talent.continent)}}</button><button v-if="canCollect" class="story-collect" @click="$emit('collect')">{{mapCopy.collected}}</button><button v-else class="story-collect" @click="$emit('close')">{{mapCopy.closeStory}}</button></footer></article></div></template>
