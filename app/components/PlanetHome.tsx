"use client";
import { lazy, Suspense, useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent, type WheelEvent as ReactWheelEvent } from "react";
import { PLATFORM_MODULES as modules } from "../config/modules";
const ThreeGlobe = lazy(() => import("./ThreeGlobe"));
type PlatformView = "planet" | "works" | "treasure";

const cosmicNodes: {view: PlatformView; label: string}[] = [
  {view: "works", label: "我的作品"},
  {view: "treasure", label: "天赋藏宝图"},
];

const starSpiritImg = "/assets/storybook/star-spirit.svg";
const floatStarsImg = "/assets/storybook/float-stars.svg";
const floatCloudImg = "/assets/storybook/float-cloud.svg";
const moduleNavArt:Record<(typeof modules)[number]["id"],string> = {
  chat:"/assets/module-nav-watercolor/nav-listening-v1.webp",
  story:"/assets/module-nav-watercolor/nav-story-v1.webp",
  build:"/assets/module-nav-watercolor/nav-build-v1.webp",
  career:"/assets/module-nav-watercolor/nav-career-v1.webp",
};

export default function PlanetHome({onNavigate}:{onNavigate:(view:PlatformView)=>void}) {
  const [orbitRotation, setOrbitRotation] = useState(0);
  const [draggingOrbit, setDraggingOrbit] = useState(false);
  const dragState = useRef({x:0, y:0, rotation:0, moved:false});
  const ignoreClick = useRef(false);
  const baseAngles = [155, 25];
  useEffect(() => {
    if (draggingOrbit || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let frame = 0;
    let lastTime = performance.now();
    const revolve = (time:number) => {
      const elapsed = Math.min(time - lastTime, 48);
      lastTime = time;
      setOrbitRotation(value => (value + elapsed * .0024) % 360);
      frame = requestAnimationFrame(revolve);
    };
    frame = requestAnimationFrame(revolve);
    return () => cancelAnimationFrame(frame);
  }, [draggingOrbit]);
  const normalizeDelta = (value:number) => ((value + 540) % 360) - 180;
  const snapToFront = (rotation:number) => {
    const delta = baseAngles.map(angle=>normalizeDelta(90-(angle+rotation))).sort((a,b)=>Math.abs(a)-Math.abs(b))[0];
    setOrbitRotation(rotation+delta);
  };
  // 拖动星轨时不使用 setPointerCapture：指针捕获会把 click 事件重定向到轨道容器，
  // 导致星石按钮的 onClick 永远收不到点击。改为拖拽期间监听 window，
  // 让松开后的 click 正常落在星石按钮上，点击星石即可跳转到对应页面。
  useEffect(() => {
    if (!draggingOrbit) return;
    const onPointerMove = (event:PointerEvent) => {
      const dx=event.clientX-dragState.current.x,dy=event.clientY-dragState.current.y;
      if(Math.hypot(dx,dy)>5) dragState.current.moved=true;
      setOrbitRotation(dragState.current.rotation+dx*.34-dy*.16);
    };
    const finishDrag = (event:PointerEvent) => {
      const dx=event.clientX-dragState.current.x,dy=event.clientY-dragState.current.y;
      setDraggingOrbit(false);
      ignoreClick.current=dragState.current.moved;
      if(dragState.current.moved) snapToFront(dragState.current.rotation+dx*.34-dy*.16);
    };
    window.addEventListener("pointermove",onPointerMove);
    window.addEventListener("pointerup",finishDrag);
    window.addEventListener("pointercancel",finishDrag);
    return () => {
      window.removeEventListener("pointermove",onPointerMove);
      window.removeEventListener("pointerup",finishDrag);
      window.removeEventListener("pointercancel",finishDrag);
    };
  }, [draggingOrbit]);
  const handleOrbitPointerDown = (event:ReactPointerEvent<HTMLElement>) => {
    dragState.current={x:event.clientX,y:event.clientY,rotation:orbitRotation,moved:false};
    ignoreClick.current=false;
    setDraggingOrbit(true);
  };
  const handleWheel = (event:ReactWheelEvent<HTMLElement>) => {
    event.preventDefault();
    setOrbitRotation(value=>value+(event.deltaY>0?-120:120));
  };
  const handleOrbitKey = (event:ReactKeyboardEvent<HTMLElement>) => {
    if(event.key!=="ArrowLeft"&&event.key!=="ArrowRight") return;
    event.preventDefault();
    setOrbitRotation(value=>value+(event.key==="ArrowLeft"?120:-120));
  };
  return <section className="planet-page three-scene-page">
    <div className="nebula-background" aria-hidden="true"/>
    <div className="nebula-drift" aria-hidden="true"/>
    <div className="space-dust" aria-hidden="true"/>
    <div className="cosmic-cloud cosmic-cloud-back" aria-hidden="true"/>
    <div className="cosmic-cloud cosmic-cloud-front" aria-hidden="true"/>
    <img className="planet-star-spirit" src={starSpiritImg} alt="" aria-hidden="true"/>
    <img className="planet-float stars" src={floatStarsImg} alt="" aria-hidden="true"/>
    <img className="planet-float cloud" src={floatCloudImg} alt="" aria-hidden="true"/>
    <div className="hero-copy"><p className="kicker">MY EXPLORATION PLANET</p><h1>转动星球，发现不一样的自己</h1><p>拖动观察梦幻星球，点击贴合球面的大陆即可直接开始探索。</p></div>
    <nav className={`cosmic-node-system ${draggingOrbit?"orbit-dragging":""}`} aria-label="个人探索功能">
      <button type="button" className="cosmic-node-orbit" aria-label="拖动或使用左右方向键旋转星轨" onPointerDown={handleOrbitPointerDown} onWheel={handleWheel} onKeyDown={handleOrbitKey}/>
      {cosmicNodes.map((node,index)=>{
        const angle=(baseAngles[index]+orbitRotation)*Math.PI/180;
        const tilt=-8*Math.PI/180;
        const ellipseX=Math.cos(angle)*44;
        const ellipseY=Math.sin(angle)*34;
        const x=50+ellipseX*Math.cos(tilt)-ellipseY*Math.sin(tilt);
        const y=50+ellipseX*Math.sin(tilt)+ellipseY*Math.cos(tilt);
        const depth=(Math.sin(angle)+1)/2;
        const isFront=depth>.82;
        return <button key={node.view} data-front={isFront||undefined} className={`cosmic-node orbit-positioned-node node-art-${index} ${x<50?"node-left":"node-right"}`} data-node-index={index} style={{left:`${x}%`,top:`${y}%`,opacity:.46+depth*.54,transform:`translate(-50%,-50%) scale(${.76+depth*.28})`,zIndex:12+Math.round(depth*8)}} onClick={()=>{if(ignoreClick.current){ignoreClick.current=false;return;}onNavigate(node.view);}}><i aria-hidden="true"/><span>{node.label}</span></button>;
      })}
      <span className="orbit-control-hint" aria-hidden="true">沿星轨缓慢环行 · 拖动选择</span>
    </nav>
    <div className="three-stage"><Suspense fallback={<div className="globe-loading">正在点亮探索星球…</div>}><ThreeGlobe/></Suspense><div className="drag-tip"><span>✥</span> 上下左右拖动 · 360° 探索 · 点击大陆进入</div></div>
    <nav className="module-dock" aria-label="四座探索大陆">
      {modules.map(item=><button key={item.id} data-module={item.id} onClick={()=>window.location.href=item.url} aria-label={`进入${item.module}，${item.name}`}>
        <i className={`module-icon ${item.color}`} aria-hidden="true"><img className="module-art" src={moduleNavArt[item.id]} alt="" draggable={false}/></i>
        <span className="module-label"><b>{item.module}</b><small>{item.name}</small></span>
      </button>)}
    </nav>
  </section>;
}
