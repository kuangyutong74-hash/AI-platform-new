"use client";

import {useEffect,useRef,useState,type PointerEvent as ReactPointerEvent} from "react";

const SETTINGS_KEY="ai-bole.platform-music.v1";
const POSITION_KEY="ai-bole.platform-music.position.v1";
const DRAG_THRESHOLD=4;
const EDGE_MARGIN=8;

type SavedPosition={x:number;y:number;unit?:"px"};

function clamp(value:number,min:number,max:number){return Math.min(Math.max(value,min),max)}

function loadPosition():SavedPosition|null{
  try{
    const raw=localStorage.getItem(POSITION_KEY);if(!raw)return null;
    const parsed=JSON.parse(raw) as Partial<SavedPosition>;
    if(typeof parsed.x!=="number"||typeof parsed.y!=="number")return null;
    if(parsed.x<0||parsed.y<0)return null;
    // 兼容旧版 0~1 的视口比例坐标，首次渲染时会转换为像素。
    return {x:parsed.x,y:parsed.y,unit:(parsed as SavedPosition).unit};
  }catch{return null}
}

function savePosition(value:SavedPosition){try{localStorage.setItem(POSITION_KEY,JSON.stringify(value))}catch{}}

export default function PlatformMusicPlayer(){
  const audioRef=useRef<HTMLAudioElement|null>(null);
  const containerRef=useRef<HTMLDivElement|null>(null);
  const firstSyncRef=useRef(true);
  const dragRef=useRef<{active:boolean;startX:number;startY:number;originX:number;originY:number;width:number;height:number;pointerId:number;moved:boolean}|null>(null);
  const frameRef=useRef<number|null>(null);
  const pendingPointRef=useRef<{x:number;y:number}|null>(null);
  const justDraggedRef=useRef(false);
  const [enabled,setEnabled]=useState(false);
  const [volume,setVolume]=useState(.28);
  const [open,setOpen]=useState(false);
  const [position,setPosition]=useState<SavedPosition|null>(null);
  const [viewport,setViewport]=useState({width:0,height:0});
  const [dragging,setDragging]=useState(false);

  useEffect(()=>{
    const move=(event:PointerEvent)=>{
      const drag=dragRef.current;if(!drag?.active)return;
      const dx=event.clientX-drag.startX,dy=event.clientY-drag.startY;
      if(!drag.moved&&Math.hypot(dx,dy)<DRAG_THRESHOLD)return;
      if(!drag.moved){drag.moved=true;setDragging(true)}
      event.preventDefault();
      const next=clampToViewport(drag.originX+dx,drag.originY+dy,drag.width,drag.height);
      pendingPointRef.current=next;
      if(frameRef.current!==null)return;
      frameRef.current=window.requestAnimationFrame(()=>{
        frameRef.current=null;
        const point=pendingPointRef.current,container=containerRef.current;
        if(!point||!container)return;
        container.style.transform=`translate3d(${Math.round(point.x-drag.originX)}px,${Math.round(point.y-drag.originY)}px,0)`;
      });
    };
    const end=(event:PointerEvent)=>{
      const drag=dragRef.current;if(!drag?.active||drag.pointerId!==event.pointerId)return;
      const moved=drag.moved;dragRef.current=null;
      if(!moved){setDragging(false);return}
      justDraggedRef.current=true;setDragging(false);
      window.setTimeout(()=>{justDraggedRef.current=false},120);
      if(frameRef.current!==null){window.cancelAnimationFrame(frameRef.current);frameRef.current=null}
      const container=containerRef.current;if(!container)return;
      const point=pendingPointRef.current;
      const next=point?clampToViewport(point.x,point.y,drag.width,drag.height):clampToViewport(drag.originX,drag.originY,drag.width,drag.height);
      pendingPointRef.current=null;
      container.style.transform="";
      const saved={...next,unit:"px" as const};setPosition(saved);savePosition(saved);
    };
    window.addEventListener("pointermove",move,{passive:false});
    window.addEventListener("pointerup",end);
    window.addEventListener("pointercancel",end);
    return()=>{
      window.removeEventListener("pointermove",move);window.removeEventListener("pointerup",end);window.removeEventListener("pointercancel",end);
      if(frameRef.current!==null)window.cancelAnimationFrame(frameRef.current);
    };
  },[]);

  useEffect(()=>{
    try{
      const saved=JSON.parse(localStorage.getItem(SETTINGS_KEY)||"null");
      if(saved){setEnabled(Boolean(saved.enabled));setVolume(typeof saved.volume==="number"?saved.volume:.28)}
    }catch{}
    setPosition(loadPosition());
  },[]);

  useEffect(()=>{
    const sync=()=>setViewport({width:window.innerWidth,height:window.innerHeight});
    sync();
    window.addEventListener("resize",sync);
    return()=>window.removeEventListener("resize",sync);
  },[]);

  useEffect(()=>{
    if(firstSyncRef.current){firstSyncRef.current=false;return}
    const audio=audioRef.current;if(!audio)return;audio.volume=volume;
    localStorage.setItem(SETTINGS_KEY,JSON.stringify({enabled,volume}));
    if(enabled){audio.play().catch(()=>setEnabled(false))}else audio.pause();
  },[enabled,volume]);

  function clampToViewport(x:number,y:number,width:number,height:number):SavedPosition{
    const maxX=Math.max(EDGE_MARGIN,window.innerWidth-width-EDGE_MARGIN);
    const maxY=Math.max(EDGE_MARGIN,window.innerHeight-height-EDGE_MARGIN);
    return {x:clamp(x,EDGE_MARGIN,maxX),y:clamp(y,EDGE_MARGIN,maxY)};
  }

  function startDrag(event:ReactPointerEvent<HTMLDivElement>){
    if(event.button!==0&&event.pointerType==="mouse")return;
    if((event.target as HTMLElement).closest(".platform-music-panel"))return;
    const container=containerRef.current;if(!container)return;
    const rect=container.getBoundingClientRect();
    dragRef.current={
      active:true,startX:event.clientX,startY:event.clientY,
      originX:rect.left,originY:rect.top,width:rect.width,height:rect.height,
      pointerId:event.pointerId,moved:false,
    };
    pendingPointRef.current={x:rect.left,y:rect.top};
  }

  const offset:React.CSSProperties=(()=>{
    if(!position||!viewport.width)return{};
    const rect=containerRef.current?.getBoundingClientRect();
    const maxX=Math.max(EDGE_MARGIN,viewport.width-(rect?.width||240));
    const maxY=Math.max(EDGE_MARGIN,viewport.height-(rect?.height||90));
    const legacy=position.unit!=="px"&&position.x<=1&&position.y<=1;
    const x=legacy?position.x*viewport.width:position.x;
    const y=legacy?position.y*viewport.height:position.y;
    return {
      left:`${clamp(x,EDGE_MARGIN,maxX)}px`,
      top:`${clamp(y,EDGE_MARGIN,maxY)}px`,
      right:"auto",bottom:"auto",
    };
  })();

  function handleToggle(){
    if(justDraggedRef.current)return;
    setEnabled(value=>!value);
  }

  function handleSettings(event:React.MouseEvent){
    if(justDraggedRef.current){event.preventDefault();event.stopPropagation();return}
    setOpen(value=>!value);
  }

  return <aside
    ref={containerRef}
    className={`platform-music ${open?"is-open":""} ${dragging?"is-dragging":""}`}
    style={offset}
    aria-label="探索背景音乐（可按住拖动位置）"
    onPointerDown={startDrag}
  >
    <audio ref={audioRef} src="/audio/exploration-theme.ogg" loop preload="metadata"/>
    <span className="platform-music-grip" aria-hidden="true"/>
    <button
      className={`platform-music-toggle ${enabled?"is-playing":""}`}
      type="button"
      aria-pressed={enabled}
      aria-label={enabled?"暂停背景音乐":"播放背景音乐"}
      onClick={handleToggle}
    >
      <span className="platform-music-star" aria-hidden="true">
        <img src="/assets/star-music-lantern-v3.png" alt="" draggable={false}/>
      </span>
      <span className="platform-music-copy"><b>星星唱机</b><small>{enabled?"正在唱歌啦":"点一下就能唱啦"}</small></span>
      <span className="platform-music-play-mark" aria-hidden="true">{enabled?"Ⅱ":"▶"}</span>
    </button>
    <button className="platform-music-settings" type="button" aria-label={open?"收起音乐设置":"展开音乐设置"} aria-expanded={open} onClick={handleSettings}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h10M18 8h2M4 16h2M10 16h10"/><circle cx="16" cy="8" r="2"/><circle cx="8" cy="16" r="2"/></svg>
    </button>
    <div className="platform-music-panel">
      <label htmlFor="platform-music-volume">背景音乐 <b>{Math.round(volume*100)}%</b></label>
      <input id="platform-music-volume" type="range" min="0" max="1" step="0.05" value={volume} onChange={event=>setVolume(Number(event.target.value))}/>
      <small>让音乐陪你探索每一座奇妙大陆。拖住唱机圆环可以挪到喜欢的位置。</small>
    </div>
  </aside>;
}
