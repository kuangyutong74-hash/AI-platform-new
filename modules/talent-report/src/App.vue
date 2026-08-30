<script setup lang="ts">
import { nextTick, ref } from "vue";
import { ElMessage } from "element-plus";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import TreasureMap from "./components/TreasureMap.vue";
import ReportBook from "./components/ReportBook.vue";
import { talents } from "./data/mockReport";
import { mapCopy } from "./data/treasureMap";

type ViewMode="child"|"adult";
const params=new URLSearchParams(location.search);
const embedded=params.get("embedded")==="1";
const forced=params.get("view");
const saved=localStorage.getItem("ai-bole-report-view");
const view=ref<ViewMode>(forced==="adult"?"adult":forced==="child"?"child":saved==="adult"?"adult":"child");
const exporting=ref(false);
function setView(value:ViewMode){if(embedded)return;view.value=value;localStorage.setItem("ai-bole-report-view",value)}
function goPlanet(){if(embedded&&window.parent!==window){window.parent.location.href="http://localhost:4173/";return}location.href="http://localhost:4173/?from=talent-report"}
async function exportPdf(){
  const formalDocument=document.querySelector<HTMLElement>(".formal-document");
  const target=formalDocument||document.querySelector<HTMLElement>(".report-main");
  if(!target)return;
  const book=document.querySelector<HTMLElement>(".magic-book-app");
  exporting.value=true;
  try{
    if(!formalDocument)book?.classList.add("export-flat");
    await nextTick();await document.fonts?.ready;
    const canvas=await html2canvas(target,{backgroundColor:formalDocument?"#FFFFFF":"#FDF3E3",scale:formalDocument?2:1.6,useCORS:true,scrollX:0,scrollY:0,width:target.scrollWidth,height:target.scrollHeight,windowWidth:target.scrollWidth,windowHeight:target.scrollHeight});
    const pdf=new jsPDF("p","mm","a4");const width=190,height=canvas.height*width/canvas.width,page=277;
    let left=height,offset=10;const image=canvas.toDataURL("image/jpeg",.94);
    pdf.addImage(image,"JPEG",10,offset,width,height);left-=page;
    while(left>0){offset=10-(height-left);pdf.addPage();pdf.addImage(image,"JPEG",10,offset,width,height);left-=page}
    pdf.save(`AI伯乐天赋报告-${new Date().toISOString().slice(0,10)}.pdf`);ElMessage.success("报告已导出");
  }catch{ElMessage.error("导出失败，请稍后重试")}
  finally{book?.classList.remove("export-flat");exporting.value=false}
}
</script>

<template>
  <div :class="['cosmos-shell',{'child-theme':view==='child',embedded}]">
    <div class="nebula nebula-a"/><div class="nebula nebula-b"/><div class="nebula nebula-c"/><div class="nebula nebula-d"/><div class="star-layer"/>
    <header v-if="!embedded" class="report-header glass">
      <button class="brand-button" @click="goPlanet"><span>✦</span><b>AI 伯乐</b><small>天赋探索报告</small></button>
      <div class="title-block"><template v-if="view==='child'"><h1>{{mapCopy.title}}</h1><p>{{mapCopy.subtitle}}</p></template><template v-else><p class="title-eyebrow">写给每一个正在发光的小朋友</p><h1>孩子的天赋星图</h1></template></div>
      <div class="view-switch single" role="group" aria-label="报告视角切换"><button class="active" @click="setView(view==='child'?'adult':'child')">{{view==='child'?'切换家长 / 老师视角':'切换孩子视角'}} →</button></div>
    </header>
    <main class="report-main">
      <section v-if="view==='child'" class="child-view"><TreasureMap :talents="talents" @open-report="setView('adult')" @back="goPlanet"/></section>
      <section v-else class="adult-view"><ReportBook :talents="talents" @back="goPlanet" @child-view="setView('child')"/></section>
    </main>
    <footer v-if="view==='adult'&&!embedded" class="report-footer glass"><p>天赋不是标签，而是一段持续被看见、被支持的成长过程。</p><div><button class="ghost" @click="goPlanet">← 回到探索星球</button><button class="primary" :disabled="exporting" @click="exportPdf">{{exporting?'正在生成…':'导出 PDF'}}</button></div></footer>
  </div>
</template>
