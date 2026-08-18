"use client";
import { lazy, Suspense } from "react";
import { PLATFORM_MODULES as modules } from "../config/modules";
const ThreeGlobe = lazy(() => import("./ThreeGlobe"));
export default function PlanetHome({onReport}:{onReport:()=>void}) {
  return <section className="planet-page three-scene-page"><div className="space-dust"/><div className="hero-copy"><p className="kicker">MY EXPLORATION PLANET</p><h1>转动星球，发现不一样的自己</h1><p>拖动观察梦幻星球，点击贴合球面的大陆即可直接开始探索。</p></div><button className="report-satellite" onClick={onReport}><span>✧</span><b>星光档案站</b><small>查看天赋报告</small></button><div className="three-stage"><Suspense fallback={<div className="globe-loading">正在点亮探索星球…</div>}><ThreeGlobe/></Suspense><div className="drag-tip"><span>✥</span> 上下左右拖动 · 360° 探索 · 点击大陆进入</div></div><div className="module-dock">{modules.map(item=><button key={item.id} onClick={()=>window.location.href=item.url}><i className={item.color}>{item.icon}</i><span><b>{item.module}</b><small>{item.name}</small></span></button>)}</div></section>;
}
