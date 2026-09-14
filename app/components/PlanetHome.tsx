"use client";
import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { loadPlatformModules, launchPlatformModule, PLATFORM_MODULES as modules, type PlatformModule } from "../config/modules";
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
    const controller = new AbortController();
    loadPlatformModules(controller.signal)
      .then(data => { if (active) setCatalog(data); })
      .catch(() => undefined);
    return () => { active = false; controller.abort(); };
  }, []);
  const launchModule = useCallback(async (item:PlatformModule) => {
    try {
      await launchPlatformModule(item);
    } catch (_) {
      // Core 不可用时仍可直接体验模块，但不会写入孩子档案。
      window.name = "";
      window.location.assign(item.url);
    }
  }, []);
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
    <div className="three-stage"><Suspense fallback={<div className="globe-loading">正在点亮探索星球…</div>}><ThreeGlobe modules={catalog} onLaunch={launchModule}/></Suspense><div className="drag-tip"><span>✥</span> 上下左右拖动 · 360° 探索 · 点击大陆进入</div></div>
    <nav className="module-dock" aria-label="四座探索大陆">
      {catalog.map(item=><button key={item.id} data-module={item.id} onClick={()=>void launchModule(item)} aria-label={`进入${item.module}，${item.name}`}>
        <i className={`module-icon ${item.color}`} aria-hidden="true">{moduleNavArt[item.id] && <img className="module-art" src={moduleNavArt[item.id]} alt="" draggable={false}/>}</i>
        <span className="module-label"><b>{item.module}</b><small>{item.name}</small></span>
      </button>)}
    </nav>
  </section>;
}
