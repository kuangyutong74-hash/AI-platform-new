"use client";

import {useEffect, useMemo, useState} from "react";
import styles from "./journey-demo.module.css";

type Stage="arrival"|"briefing"|"choices"|"task"|"career"|"complete";
type TaskId="story"|"deepsea"|"career";

const taskData:Record<TaskId,{title:string;label:string;copy:string;art:string;color:string;url:string}>={
  story:{title:"找回小海龟的记忆",label:"翻开那张湿漉漉的故事页",copy:"它记得会发光的海葵，却想不起洋流到来以后发生了什么。你愿意陪它把故事接下去吗？",art:"/assets/module-nav-watercolor/nav-story-v1.webp",color:"rose",url:"http://localhost:5174/story-create?from=journey-demo"},
  deepsea:{title:"去基地看看哪里坏了",label:"带着线索潜入深海",copy:"海底的灯还在一闪一闪。也许线路断了，也许有小动物住错了地方，需要你亲手检查。",art:"/assets/module-nav-watercolor/nav-build-v1.webp",color:"blue",url:"http://localhost:3001/?from=journey-demo"},
  career:{title:"借一张今天的工作证",label:"试试怎样照顾和帮助别人",copy:"阿拾找到了六座职业小岛。它会推荐两座，但最后去哪里，由你自己决定。",art:"/assets/module-nav-watercolor/nav-career-v1.webp",color:"amber",url:"http://localhost:8000/careers?from=journey-demo"},
};

const careers=[
  {id:"doctor",name:"社区医生",note:"先听一听哪里不舒服",tone:"mint"},
  {id:"animal_caretaker",name:"动物保护员",note:"观察并照顾需要帮助的动物",tone:"leaf"},
  {id:"firefighter",name:"消防员",note:"在紧急时刻保护大家",tone:"coral"},
  {id:"teacher",name:"小学教师",note:"帮助每个孩子学会新事情",tone:"sun"},
  {id:"chef",name:"餐厅厨师",note:"安排食材和厨房里的工作",tone:"orange"},
  {id:"journalist",name:"报社记者",note:"提问、核实并记录真实故事",tone:"violet"},
];

export default function JourneyDemo(){
  const [stage,setStage]=useState<Stage>("arrival");
  const [activeTask,setActiveTask]=useState<TaskId>("story");
  const [completed,setCompleted]=useState<TaskId[]>([]);
  const [career,setCareer]=useState("doctor");
  const finished=completed.length===3;
  const progress=useMemo(()=>completed.length,[completed]);

  useEffect(()=>{window.scrollTo(0,0);},[stage]);

  const enterTask=(id:TaskId)=>{setActiveTask(id);setStage(id==="career"?"career":"task");};
  const finishTask=(id:TaskId)=>{
    setCompleted(items=>items.includes(id)?items:[...items,id]);
    setStage(completed.length>=2?"complete":"choices");
  };
  const reset=()=>{setStage("arrival");setCompleted([]);setCareer("doctor");setActiveTask("story");};

  return <main className={styles.demo} data-stage={stage}>
    <div className={styles.sky} aria-hidden="true"/>
    <header className={styles.header}>
      <a href="/" className={styles.brand}><img src="/assets/watercolor-brand-planet-v1.png" alt=""/><span><b>AI 伯乐</b><small>水彩探索旅程 · 交互演示</small></span></a>
      <div className={styles.progress} aria-label={`已完成 ${progress} 个体验`}><span>{progress}/3</span><i className={completed.includes("story")?styles.done:""}/><i className={completed.includes("deepsea")?styles.done:""}/><i className={completed.includes("career")?styles.done:""}/></div>
      <button className={styles.quietButton} onClick={reset}>重新演示</button>
    </header>

    {stage==="arrival"&&<section className={styles.arrival} aria-labelledby="arrival-title">
      <div className={styles.planetScene}>
        <img className={styles.planet} src="/assets/watercolor-brand-planet-v1.png" alt="水彩探索星球"/>
        <span className={styles.orbit}/><span className={styles.starOne}/><span className={styles.starTwo}/>
        <img className={styles.guideFlying} src="/assets/storybook/ashi-guide-watercolor-v1.png" alt="拾光鸟阿拾从星球后面飞出来"/>
      </div>
      <div className={styles.arrivalCopy}>
        <h1 id="arrival-title">今天，星球背面传来了一点奇怪的光</h1>
        <p>阿拾刚刚绕着星球飞了一圈，它好像发现了一件需要你帮忙的事。</p>
        <button className={styles.bookmarkButton} onClick={()=>setStage("briefing")}>听阿拾说说</button>
        <small>这是前端流程 Demo，不会写入孩子的正式记录。</small>
      </div>
    </section>}

    {stage==="briefing"&&<section className={styles.bookStage} aria-labelledby="brief-title">
      <div className={styles.scenePage}><img src="/assets/collections/growth/ocean-island-720.webp" alt="安静的水彩海底小岛"/><span className={styles.signal}>一闪…一闪…</span></div>
      <div className={styles.talkPage}>
        <img className={styles.guidePerched} src="/assets/storybook/ashi-guide-watercolor-v1.png" alt="拾光鸟阿拾"/>
        <div className={styles.speech}><b>阿拾</b><h1 id="brief-title">我在海面下面看见一盏忽明忽暗的灯。</h1><p>灯旁边还有一个小小的影子，一直绕着同一个地方游。我们先去听听它想说什么，好吗？</p></div>
        <div className={styles.answerRow} aria-label="选择回应"><button onClick={()=>setStage("choices")}>它是不是迷路了？</button><button onClick={()=>setStage("choices")}>它可能需要帮助</button><button onClick={()=>setStage("choices")}>我们去看看吧</button></div>
        <button className={styles.speakButton} onClick={()=>setStage("choices")}>我想自己说一句</button>
      </div>
    </section>}

    {stage==="choices"&&<section className={styles.choiceStage} aria-labelledby="choice-title">
      <div className={styles.chatRail}>
        <img src="/assets/storybook/ashi-guide-watercolor-v1.png" alt="阿拾"/>
        <div><b>阿拾</b><p>小海龟说不清发生了什么，不过它留下了三条线索。你想先看哪一条？</p><small>三张都可以体验，顺序由你决定。</small></div>
      </div>
      <div className={styles.paperHeading}><h1 id="choice-title">选择下一页</h1><p>{completed.length===0?"先选最吸引你的那张，其他两张会替你夹好书签。":"欢迎回来。还亮着的画页，正在等你继续。"}</p></div>
      <div className={styles.taskSpread}>
        {(Object.keys(taskData) as TaskId[]).map((id,index)=>{const task=taskData[id],done=completed.includes(id);return <button key={id} className={`${styles.taskCard} ${styles[task.color]} ${done?styles.completed:""}`} onClick={()=>!done&&enterTask(id)} disabled={done} style={{"--tilt":`${index===0?-2:index===1?1.5:-1}deg`} as React.CSSProperties}>
          <img src={task.art} alt=""/><span className={styles.cardIndex}>{done?"已经看过":"线索画页"}</span><h2>{task.title}</h2><p>{task.label}</p><b>{done?"已收进故事书":"打开看看"}</b>
        </button>})}
      </div>
      <p className={styles.choiceNote}>实际接入时，打开画页会进入现有故事、深海或职业服务；完成后自动回到这段对话。</p>
    </section>}

    {stage==="task"&&<section className={styles.modulePreview} aria-labelledby="task-title">
      <nav className={styles.journeyBar}><button onClick={()=>setStage("choices")}>返回阿拾</button><span>帮小海龟找到回家的路</span><small>自动保存</small></nav>
      <div className={`${styles.moduleScene} ${styles[taskData[activeTask].color]}`}>
        <img src={taskData[activeTask].art} alt=""/>
        <div><span>{activeTask==="story"?"故事共创画页":"深海基地画页"}</span><h1 id="task-title">{taskData[activeTask].title}</h1><p>{taskData[activeTask].copy}</p><div className={styles.moduleActions}><a href={taskData[activeTask].url}>打开现有模块</a><button onClick={()=>finishTask(activeTask)}>模拟完成并返回聊天</button></div></div>
      </div>
      <aside className={styles.bridgeNote}><img src="/assets/storybook/ashi-guide-watercolor-v1.png" alt=""/><p><b>为什么这一步自然发生？</b>前一段聊天只发现“灯和小海龟”，这张画页负责找到原因或亲手解决问题；完成结果会被阿拾带回聊天继续引用。</p></aside>
    </section>}

    {stage==="career"&&<section className={styles.careerStage} aria-labelledby="career-title">
      <nav className={styles.journeyBar}><button onClick={()=>setStage("choices")}>返回阿拾</button><span>借一张今天的工作证</span><small>现有六个职业</small></nav>
      <div className={styles.careerIntro}><img src="/assets/storybook/ashi-guide-watercolor-v1.png" alt="阿拾"/><div><h1 id="career-title">阿拾先找到了两座可能有关的职业岛</h1><p>因为你一直在留意小海龟需不需要帮助，所以先推荐社区医生和动物保护员。你也可以自己选择其他职业。</p></div></div>
      <div className={styles.careerMap}>
        {careers.map((item,index)=><button key={item.id} className={`${styles.careerIsland} ${styles[item.tone]} ${career===item.id?styles.selected:""}`} onClick={()=>setCareer(item.id)}><span>{index<2?"这次推荐":"也可以选"}</span><h2>{item.name}</h2><p>{item.note}</p></button>)}
      </div>
      <div className={styles.careerFooter}><p>推荐只解释“为什么可能相关”，不会替孩子决定，也不会新增职业。</p><div><a href={`http://localhost:8000/workday/${career}?from=journey-demo`}>打开现有职业体验</a><button onClick={()=>finishTask("career")}>模拟体验完成</button></div></div>
    </section>}

    {stage==="complete"&&<section className={styles.completeStage} aria-labelledby="complete-title">
      <img className={styles.completeGuide} src="/assets/storybook/ashi-guide-watercolor-v1.png" alt="阿拾带回三枚书签"/>
      <div className={styles.completedBook} aria-hidden="true"><span/><i/><b/></div>
      <div><h1 id="complete-title">三张画页都回到故事里了</h1><p>你听见了小海龟的求助，也从不同方向把这件事看完整。正式版本会在这里引用孩子真实说过的话、做过的调整和选择的职业。</p><blockquote>“我想先看看它有没有受伤，再帮它把回家的灯修好。”</blockquote><button className={styles.bookmarkButton} onClick={reset}>再看一次完整流程</button></div>
      {!finished&&<button onClick={()=>setStage("choices")}>还有画页没看完</button>}
    </section>}
  </main>;
}
