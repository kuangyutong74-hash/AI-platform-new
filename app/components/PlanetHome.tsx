"use client";
import { lazy, Suspense, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent, type WheelEvent as ReactWheelEvent } from "react";
import { PLATFORM_MODULES as modules } from "../config/modules";
const ThreeGlobe = lazy(() => import("./ThreeGlobe"));
type PlatformView = "planet" | "works" | "timeline" | "report";

const cosmicNodes: {view: PlatformView; label: string}[] = [
  {view: "works", label: "我的作品"},
  {view: "timeline", label: "成长足迹"},
  {view: "report", label: "天赋报告"},
];

export default function PlanetHome({onNavigate}:{onNavigate:(view:PlatformView)=>void}) {
  const [orbitRotation, setOrbitRotation] = useState(0);
  const [draggingOrbit, setDraggingOrbit] = useState(false);
  const dragState = useRef({x:0, y:0, rotation:0, moved:false});
  const ignoreClick = useRef(false);
  const baseAngles = [155, 270, 25];
  const normalizeDelta = (value:number) => ((value + 540) % 360) - 180;
  const snapToFront = (rotation:number) => {
    const delta = baseAngles.map(angle=>normalizeDelta(90-(angle+rotation))).sort((a,b)=>Math.abs(a)-Math.abs(b))[0];
    setOrbitRotation(rotation+delta);
  };
  const handleOrbitPointerDown = (event:ReactPointerEvent<HTMLElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    dragState.current={x:event.clientX,y:event.clientY,rotation:orbitRotation,moved:false};
    setDraggingOrbit(true);
  };
  const handleOrbitPointerMove = (event:ReactPointerEvent<HTMLElement>) => {
    if(!event.currentTarget.hasPointerCapture(event.pointerId)) return;
    const dx=event.clientX-dragState.current.x,dy=event.clientY-dragState.current.y;
    if(Math.hypot(dx,dy)>5) dragState.current.moved=true;
    setOrbitRotation(dragState.current.rotation+dx*.34-dy*.16);
  };
  const handleOrbitPointerUp = (event:ReactPointerEvent<HTMLElement>) => {
    if(event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    setDraggingOrbit(false);
    ignoreClick.current=dragState.current.moved;
    if(dragState.current.moved) snapToFront(orbitRotation);
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
    <div className="stardust-fragment fragment-left" aria-hidden="true"/>
    <div className="stardust-fragment fragment-right" aria-hidden="true"/>
    <div className="cosmic-cloud cosmic-cloud-back" aria-hidden="true"/>
    <div className="cosmic-cloud cosmic-cloud-front" aria-hidden="true"/>
    <div className="hero-copy"><p className="kicker">MY EXPLORATION PLANET</p><h1>转动星球，发现不一样的自己</h1><p>拖动观察梦幻星球，点击贴合球面的大陆即可直接开始探索。</p></div>
    <nav className={`cosmic-node-system ${draggingOrbit?"orbit-dragging":""}`} aria-label="个人探索功能，可拖动星轨切换" tabIndex={0} onPointerDown={handleOrbitPointerDown} onPointerMove={handleOrbitPointerMove} onPointerUp={handleOrbitPointerUp} onPointerCancel={handleOrbitPointerUp} onWheel={handleWheel} onKeyDown={handleOrbitKey}>
      <div className="cosmic-node-orbit" aria-hidden="true"/>
      {cosmicNodes.map((node,index)=>{
        const angle=(baseAngles[index]+orbitRotation)*Math.PI/180;
        const tilt=-8*Math.PI/180;
        const ellipseX=Math.cos(angle)*44;
        const ellipseY=Math.sin(angle)*34;
        const x=50+ellipseX*Math.cos(tilt)-ellipseY*Math.sin(tilt);
        const y=50+ellipseX*Math.sin(tilt)+ellipseY*Math.cos(tilt);
        const depth=(Math.sin(angle)+1)/2;
        const isFront=depth>.82;
        return <button key={node.view} data-front={isFront||undefined} className={`cosmic-node orbit-positioned-node ${x<50?"node-left":"node-right"}`} style={{left:`${x}%`,top:`${y}%`,opacity:.46+depth*.54,transform:`translate(-50%,-50%) scale(${.76+depth*.28})`,zIndex:12+Math.round(depth*8)}} onClick={()=>{if(ignoreClick.current){ignoreClick.current=false;return;}onNavigate(node.view);}}><i aria-hidden="true"/><span>{node.label}</span></button>;
      })}
      <span className="orbit-control-hint" aria-hidden="true">拖动星轨 · 滑动选择</span>
    </nav>
    <div className="three-stage"><Suspense fallback={<div className="globe-loading">正在点亮探索星球…</div>}><ThreeGlobe/></Suspense><div className="drag-tip"><span>✥</span> 上下左右拖动 · 360° 探索 · 点击大陆进入</div></div>
    <div className="module-dock">{modules.map(item=><button key={item.id} onClick={()=>window.location.href=item.url}><i className={item.color}>{item.icon}</i><span><b>{item.module}</b><small>{item.name}</small></span></button>)}</div>
  </section>;
}
