"use client";
import { lazy, Suspense, useEffect, useState } from "react";
import { CORE_API_URL, PLATFORM_MODULES as modules } from "../config/modules";
const ThreeGlobe = lazy(() => import("./ThreeGlobe"));
type PlatformView = "planet" | "works" | "treasure";

const cosmicNodes: {view: PlatformView; label: string}[] = [
  {view: "works", label: "我的作品"},
  {view: "treasure", label: "天赋藏宝图"},
];

const starSpiritImg = "/assets/storybook/star-spirit.svg";
const floatStarsImg = "/assets/storybook/float-stars.svg";
const floatCloudImg = "/assets/storybook/float-cloud.svg";
const moduleNavArt:Record<string,string> = {
  chat:"/assets/module-nav-watercolor/nav-listening-v1.webp",
  story:"/assets/module-nav-watercolor/nav-story-v1.webp",
  build:"/assets/module-nav-watercolor/nav-build-v1.webp",
  career:"/assets/module-nav-watercolor/nav-career-v1.webp",
};

export default function PlanetHome({onNavigate}:{onNavigate:(view:PlatformView)=>void}) {
  const [catalog, setCatalog] = useState(modules);
  useEffect(() => {
    let active = true;
    fetch(`${CORE_API_URL}/api/v1/modules`)
      .then(response => response.ok ? response.json() : Promise.reject())
      .then(data => {
        if (!active || !Array.isArray(data.modules)) return;
        setCatalog(data.modules.map((manifest: {id:string;name:string;description?:string;entryUrl:string;healthUrl?:string}, index:number) => {
          const existing = modules.find(item => (item.id === "build" ? "deep_sea" : item.id) === manifest.id);
          return existing ? {...existing, name: manifest.name, desc: manifest.description || existing.desc, url: manifest.entryUrl, healthUrl: manifest.healthUrl || existing.healthUrl} : {id: manifest.id, name: manifest.name, module: manifest.name, icon: "✦", iconAsset: "", angle: (index * 73) % 360, latitude: index % 2 ? -22 : 22, url: manifest.entryUrl, healthUrl: manifest.healthUrl || "", color: "mint" as const, desc: manifest.description || "新的探索体验"};
        }));
      })
      .catch(() => undefined);
    return () => { active = false; };
  }, []);
  const launchModule = async (item:(typeof catalog)[number]) => {
    const moduleId = item.id === "build" ? "deep_sea" : item.id;
    try {
      const response = await fetch(`${CORE_API_URL}/api/v1/assessment-sessions`, {method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({module_id:moduleId})});
      if (!response.ok) throw new Error("session unavailable");
      const context = await response.json();
      window.name = JSON.stringify({namespace:"ai-bole.launch-context.v1",context});
    } catch (_) {
      // Core 不可用时仍可直接体验模块，但不会写入孩子档案。
      window.name = "";
    }
    window.location.href = item.url;
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
    <nav className="personal-landmarks" aria-label="个人探索功能">
      {cosmicNodes.map((node,index)=><button key={node.view} className={`personal-landmark personal-landmark-${index===0?"left":"right"}`} data-node-index={index} onClick={()=>onNavigate(node.view)}><i aria-hidden="true"/><span>{node.label}</span></button>)}
    </nav>
    <div className="three-stage"><Suspense fallback={<div className="globe-loading">正在点亮探索星球…</div>}><ThreeGlobe/></Suspense><div className="drag-tip"><span>✥</span> 上下左右拖动 · 360° 探索 · 点击大陆进入</div></div>
    <nav className="module-dock" aria-label="四座探索大陆">
      {catalog.map(item=><button key={item.id} data-module={item.id} onClick={()=>void launchModule(item)} aria-label={`进入${item.module}，${item.name}`}>
        <i className={`module-icon ${item.color}`} aria-hidden="true">{moduleNavArt[item.id] && <img className="module-art" src={moduleNavArt[item.id]} alt="" draggable={false}/>}</i>
        <span className="module-label"><b>{item.module}</b><small>{item.name}</small></span>
      </button>)}
    </nav>
  </section>;
}
