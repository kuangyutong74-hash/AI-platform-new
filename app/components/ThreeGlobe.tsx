"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { CSS2DObject, CSS2DRenderer } from "three/examples/jsm/renderers/CSS2DRenderer.js";
import { PLATFORM_MODULES as modules } from "../config/modules";

const TEXTURE_WIDTH = 2048;
const TEXTURE_HEIGHT = 1024;
const islandCenters = [
  { x: .52, y: .30, rx: .105, ry: .115 },
  { x: .76, y: .55, rx: .115, ry: .12 },
  { x: .28, y: .51, rx: .12, ry: .105 },
  { x: .08, y: .67, rx: .105, ry: .115 },
];
const islandColors = ["#9ccdb9", "#b8a5d3", "#9ebbd1", "#ddc58d"];

function organicIslandPath(center: typeof islandCenters[number], seed: number) {
  const path = new Path2D();
  const points = Array.from({ length: 28 }, (_, index) => {
    const angle = index / 28 * Math.PI * 2;
    const bays = Math.sin(angle * 3 + seed) * .13 + Math.sin(angle * 7 - seed * .7) * .07 + Math.cos(angle * 11 + seed) * .035;
    const peninsula = index === (4 + seed * 3 | 0) % 28 || index === (17 + seed * 2 | 0) % 28 ? .2 : 0;
    const variation = .83 + bays + peninsula;
    return { x: (center.x + Math.cos(angle) * center.rx * variation) * TEXTURE_WIDTH, y: (center.y + Math.sin(angle) * center.ry * variation) * TEXTURE_HEIGHT };
  });
  const first = points[0], last = points.at(-1)!;
  path.moveTo((first.x + last.x) / 2, (first.y + last.y) / 2);
  points.forEach((point, index) => { const next = points[(index + 1) % points.length]; path.quadraticCurveTo(point.x, point.y, (point.x + next.x) / 2, (point.y + next.y) / 2); });
  path.closePath();
  return path;
}

function createPlanetTextures() {
  const surface = document.createElement("canvas"), ids = document.createElement("canvas"), clouds = document.createElement("canvas"), hover = document.createElement("canvas"), landMask = document.createElement("canvas");
  for (const canvas of [surface, ids, clouds, hover, landMask]) { canvas.width = TEXTURE_WIDTH; canvas.height = TEXTURE_HEIGHT; }
  const ctx = surface.getContext("2d")!, idCtx = ids.getContext("2d", { willReadFrequently: true })!, cloudCtx = clouds.getContext("2d")!, hoverCtx = hover.getContext("2d")!;
  const islandPaths: Path2D[] = [];
  const ocean = ctx.createLinearGradient(0, 0, TEXTURE_WIDTH, TEXTURE_HEIGHT); ocean.addColorStop(0, "#173f72"); ocean.addColorStop(.46, "#0c315f"); ocean.addColorStop(1, "#071d45"); ctx.fillStyle = ocean; ctx.fillRect(0, 0, TEXTURE_WIDTH, TEXTURE_HEIGHT);
  for (let i = 0; i < 5200; i++) { const x = Math.random()*TEXTURE_WIDTH, y = Math.random()*TEXTURE_HEIGHT, a = Math.random()*.055; ctx.fillStyle = `rgba(119,184,216,${a})`; ctx.fillRect(x,y,Math.random()*3+1,1); }
  modules.forEach((module, index) => {
    const center = islandCenters[index], path = organicIslandPath(center, index * 1.7 + .4); islandPaths.push(path);
    ctx.save(); ctx.shadowColor = "rgba(4,25,39,.34)"; ctx.shadowBlur = 20; ctx.shadowOffsetY = 9; ctx.fillStyle = islandColors[index]; ctx.fill(path); ctx.clip(path);
    const terrain = ctx.createRadialGradient(center.x*TEXTURE_WIDTH,center.y*TEXTURE_HEIGHT,10,center.x*TEXTURE_WIDTH,center.y*TEXTURE_HEIGHT,center.rx*TEXTURE_WIDTH); terrain.addColorStop(0,"rgba(255,255,255,.32)"); terrain.addColorStop(.55,"rgba(255,255,255,.04)"); terrain.addColorStop(1,"rgba(41,73,67,.24)"); ctx.fillStyle=terrain; ctx.fillRect(0,0,TEXTURE_WIDTH,TEXTURE_HEIGHT);
    for(let j=0;j<20;j++){ctx.strokeStyle=`rgba(67,91,82,${.05+j%3*.025})`;ctx.lineWidth=2;ctx.beginPath();ctx.arc(center.x*TEXTURE_WIDTH+(j%5-2)*25,center.y*TEXTURE_HEIGHT+(Math.floor(j/5)-2)*19,18+j%4*8,0,Math.PI*1.3);ctx.stroke();} ctx.restore();
    ctx.textAlign="center"; ctx.fillStyle="rgba(27,46,57,.88)"; ctx.font="600 34px 'Microsoft YaHei',sans-serif"; ctx.fillText(module.name,center.x*TEXTURE_WIDTH,center.y*TEXTURE_HEIGHT-4); ctx.font="500 20px 'Microsoft YaHei',sans-serif"; ctx.fillText(module.module,center.x*TEXTURE_WIDTH,center.y*TEXTURE_HEIGHT+29);
    idCtx.fillStyle = `rgb(${index+1},0,0)`; idCtx.fill(path);
  });
  cloudCtx.filter="blur(13px)";
  for(let i=0;i<170;i++){const x=Math.random()*TEXTURE_WIDTH,y=Math.random()*TEXTURE_HEIGHT,w=40+Math.random()*180,h=7+Math.random()*25;const g=cloudCtx.createRadialGradient(x,y,0,x,y,w/2);g.addColorStop(0,`rgba(255,255,255,${.08+Math.random()*.18})`);g.addColorStop(1,"rgba(255,255,255,0)");cloudCtx.fillStyle=g;cloudCtx.beginPath();cloudCtx.ellipse(x,y,w,h,Math.random()*.4,0,Math.PI*2);cloudCtx.fill();}
  return { surface: new THREE.CanvasTexture(surface), clouds: new THREE.CanvasTexture(clouds), hover: new THREE.CanvasTexture(hover), hoverCtx, landMask, islandPaths, idCtx };
}

export default function ThreeGlobe() {
  const hostRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const host = hostRef.current!; const scene = new THREE.Scene(); const camera = new THREE.PerspectiveCamera(34,1,.1,100); camera.position.set(0,.12,7.4);
    const renderer = new THREE.WebGLRenderer({ antialias:true, alpha:true, powerPreference:"high-performance" }); renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.outputColorSpace=THREE.SRGBColorSpace; renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=.94; host.appendChild(renderer.domElement);
    const labelRenderer=new CSS2DRenderer();labelRenderer.domElement.className="globe-label-layer";host.appendChild(labelRenderer.domElement);
    const labelElement=document.createElement("div");labelElement.className="surface-label";const labelInner=document.createElement("div");labelInner.className="surface-label-inner";const diamond=document.createElement("span");diamond.textContent="◇";const copy=document.createElement("div");const title=document.createElement("b"),subtitle=document.createElement("small");copy.append(title,subtitle);const arrow=document.createElement("em");arrow.textContent="→";const guide=document.createElement("i");labelInner.append(diamond,copy,arrow,guide);labelElement.append(labelInner);const labelObject=new CSS2DObject(labelElement);labelObject.visible=false;scene.add(labelObject);
    const textures=createPlanetTextures(); textures.surface.colorSpace=THREE.SRGBColorSpace; textures.clouds.colorSpace=THREE.SRGBColorSpace;
    const loader=new THREE.TextureLoader();
    let interactionReady=false;
    const themedSurface=loader.load("/textures/fantasy-continents-themed-v2.png", texture=>{
      const sample=document.createElement("canvas");sample.width=TEXTURE_WIDTH;sample.height=TEXTURE_HEIGHT;const sampleCtx=sample.getContext("2d",{willReadFrequently:true})!;sampleCtx.drawImage(texture.image,0,0,TEXTURE_WIDTH,TEXTURE_HEIGHT);
      const source=sampleCtx.getImageData(0,0,TEXTURE_WIDTH,TEXTURE_HEIGHT),idImage=textures.idCtx.createImageData(TEXTURE_WIDTH,TEXTURE_HEIGHT),maskCtx=textures.landMask.getContext("2d")!,maskImage=maskCtx.createImageData(TEXTURE_WIDTH,TEXTURE_HEIGHT);
      for(let offset=0;offset<source.data.length;offset+=4){const r=source.data[offset],g=source.data[offset+1],b=source.data[offset+2],luma=r*.2126+g*.7152+b*.0722,land=luma>112;const pixel=offset/4,x=pixel%TEXTURE_WIDTH,y=Math.floor(pixel/TEXTURE_WIDTH);const moduleIndex=y<TEXTURE_HEIGHT/2?(x<TEXTURE_WIDTH/2?1:0):(x<TEXTURE_WIDTH/2?2:3);idImage.data[offset]=land?moduleIndex+1:0;idImage.data[offset+3]=255;const alpha=Math.max(0,Math.min(255,(luma-92)*8));maskImage.data[offset]=255;maskImage.data[offset+1]=255;maskImage.data[offset+2]=255;maskImage.data[offset+3]=alpha;}
      textures.idCtx.putImageData(idImage,0,0);maskCtx.putImageData(maskImage,0,0);interactionReady=true;
    }); themedSurface.colorSpace=THREE.SRGBColorSpace; themedSurface.anisotropy=renderer.capabilities.getMaxAnisotropy();
    const originalSurface=loader.load("/textures/fantasy-continents-equirectangular-v1.png"); originalSurface.colorSpace=THREE.SRGBColorSpace; originalSurface.anisotropy=renderer.capabilities.getMaxAnisotropy();
    const sphereGeometry=new THREE.SphereGeometry(2,96,96); const globe=new THREE.Mesh(sphereGeometry,new THREE.MeshStandardMaterial({map:themedSurface,roughness:.9,metalness:0})); globe.rotation.y=-.35; scene.add(globe);
    const originalDetailLayer=new THREE.Mesh(new THREE.SphereGeometry(2.002,96,96),new THREE.MeshLambertMaterial({map:originalSurface,transparent:true,opacity:.16,depthWrite:false})); originalDetailLayer.rotation.copy(globe.rotation); scene.add(originalDetailLayer);
    const hoverLayer=new THREE.Mesh(new THREE.SphereGeometry(2.006,96,96),new THREE.MeshBasicMaterial({map:textures.hover,transparent:true,opacity:.8,depthWrite:false,blending:THREE.AdditiveBlending})); hoverLayer.rotation.copy(globe.rotation); scene.add(hoverLayer);
    const cloudLayer=new THREE.Mesh(new THREE.SphereGeometry(2.035,80,80),new THREE.MeshLambertMaterial({map:textures.clouds,transparent:true,opacity:.72,depthWrite:false})); cloudLayer.rotation.y=.2; scene.add(cloudLayer);
    const atmosphere=new THREE.Mesh(new THREE.SphereGeometry(2.13,80,80),new THREE.ShaderMaterial({side:THREE.BackSide,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false,uniforms:{glowColor:{value:new THREE.Color("#79cfff")},viewVector:{value:camera.position}},vertexShader:`varying vec3 n;varying vec3 p;void main(){n=normalize(normalMatrix*normal);p=(modelViewMatrix*vec4(position,1.)).xyz;gl_Position=projectionMatrix*vec4(p,1.);}`,fragmentShader:`uniform vec3 glowColor;varying vec3 n;varying vec3 p;void main(){float i=pow(.72-dot(n,normalize(-p)),3.2);gl_FragColor=vec4(glowColor,i*.64);}`})); scene.add(atmosphere);
    scene.add(new THREE.HemisphereLight("#b9d6ff","#13132d",1.25)); const key=new THREE.DirectionalLight("#fff4e8",2.15);key.position.set(-4,3,5);scene.add(key);const rim=new THREE.DirectionalLight("#7aa7ff",.55);rim.position.set(4,-1,-4);scene.add(rim);
    const starGeometry=new THREE.BufferGeometry(),starPositions=new Float32Array(1500*3);for(let i=0;i<starPositions.length;i+=3){const r=18+Math.random()*30,theta=Math.random()*Math.PI*2,phi=Math.acos(2*Math.random()-1);starPositions[i]=r*Math.sin(phi)*Math.cos(theta);starPositions[i+1]=r*Math.cos(phi);starPositions[i+2]=r*Math.sin(phi)*Math.sin(theta);}starGeometry.setAttribute("position",new THREE.BufferAttribute(starPositions,3));scene.add(new THREE.Points(starGeometry,new THREE.PointsMaterial({color:"#dcd7ff",size:.035,transparent:true,opacity:.72})));
    const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.055;controls.enablePan=false;controls.enableZoom=false;controls.rotateSpeed=.48;controls.autoRotate=true;controls.autoRotateSpeed=.32;
    const raycaster=new THREE.Raycaster(),mouse=new THREE.Vector2(),labelNormal=new THREE.Vector3(0,0,1),projectedLabel=new THREE.Vector3(),projectedCenter=new THREE.Vector3();let down={x:0,y:0},hovered=-1,pending=-1,active=-1,reveal=0,revealTarget=0,pointerDown=false,hoverTimer:ReturnType<typeof setTimeout>|null=null;
    const setHover=(index:number)=>{if(index===hovered)return;hovered=index;textures.hoverCtx.clearRect(0,0,TEXTURE_WIDTH,TEXTURE_HEIGHT);if(index>=0&&interactionReady){const quadrants=[{x:TEXTURE_WIDTH/2,y:0},{x:0,y:0},{x:0,y:TEXTURE_HEIGHT/2},{x:TEXTURE_WIDTH/2,y:TEXTURE_HEIGHT/2}],q=quadrants[index];textures.hoverCtx.save();textures.hoverCtx.beginPath();textures.hoverCtx.rect(q.x,q.y,TEXTURE_WIDTH/2,TEXTURE_HEIGHT/2);textures.hoverCtx.clip();textures.hoverCtx.shadowColor="rgba(154,215,255,.9)";textures.hoverCtx.shadowBlur=34;textures.hoverCtx.drawImage(textures.landMask,0,0);textures.hoverCtx.globalCompositeOperation="source-in";textures.hoverCtx.fillStyle="rgba(255,255,255,.28)";textures.hoverCtx.fillRect(q.x,q.y,TEXTURE_WIDTH/2,TEXTURE_HEIGHT/2);textures.hoverCtx.restore();}textures.hover.needsUpdate=true;};
    const hideLabel=()=>{if(hoverTimer)clearTimeout(hoverTimer);hoverTimer=null;pending=-1;revealTarget=0;setHover(-1);};
    const requestLabel=(index:number,point:THREE.Vector3)=>{labelNormal.copy(point).normalize();if(index===active){revealTarget=1;return;}if(index===pending)return;if(hoverTimer)clearTimeout(hoverTimer);pending=index;hoverTimer=setTimeout(()=>{active=index;pending=-1;title.textContent=modules[index].name;subtitle.textContent=modules[index].module;labelInner.className=`surface-label-inner ${modules[index].color}`;setHover(index);revealTarget=1;labelObject.visible=true;},150);};
    const pick=(event:PointerEvent,navigate:boolean)=>{if(!interactionReady)return;const rect=renderer.domElement.getBoundingClientRect();mouse.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(mouse,camera);const hit=raycaster.intersectObject(globe)[0];if(!hit?.uv){renderer.domElement.style.cursor="grab";hideLabel();return;}const pixel=textures.idCtx.getImageData(Math.floor(hit.uv.x*TEXTURE_WIDTH),Math.floor((1-hit.uv.y)*TEXTURE_HEIGHT),1,1).data[0]-1;const valid=pixel>=0&&pixel<modules.length;renderer.domElement.style.cursor=valid?"pointer":"grab";if(valid)requestLabel(pixel,hit.point);else hideLabel();if(navigate&&valid)window.location.href=modules[pixel].url;};
    const onDown=(e:PointerEvent)=>{down={x:e.clientX,y:e.clientY};pointerDown=true;};const onUp=(e:PointerEvent)=>{pointerDown=false;if(Math.hypot(e.clientX-down.x,e.clientY-down.y)<6)pick(e,true);};const onMove=(e:PointerEvent)=>{if(!pointerDown)pick(e,false);};const onLeave=()=>{pointerDown=false;hideLabel();};renderer.domElement.addEventListener("pointerdown",onDown);renderer.domElement.addEventListener("pointerup",onUp);renderer.domElement.addEventListener("pointermove",onMove);renderer.domElement.addEventListener("pointerleave",onLeave);
    const resize=()=>{const width=host.clientWidth,height=host.clientHeight;renderer.setSize(width,height,false);labelRenderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();};const observer=new ResizeObserver(resize);observer.observe(host);resize();let frame=0,last=performance.now();const animate=(now:number)=>{frame=requestAnimationFrame(animate);const delta=Math.min((now-last)/1000,.05);last=now;cloudLayer.rotation.y+=delta*.012;controls.update();reveal+= (revealTarget-reveal)*Math.min(1,delta*9);const surfacePoint=labelNormal.clone().multiplyScalar(2),towardCamera=camera.position.clone().sub(surfacePoint).normalize(),frontFacing=labelNormal.dot(towardCamera)>.035;if(!frontFacing&&active>=0){labelObject.visible=false;revealTarget=0;setHover(-1);}else labelObject.visible=reveal>.012;labelObject.position.copy(labelNormal).multiplyScalar(1.94+reveal*.29);projectedLabel.copy(labelObject.position).project(camera);projectedCenter.set(0,0,0).project(camera);const tilt=THREE.MathUtils.clamp((projectedLabel.x-projectedCenter.x)*13,-8,8);labelInner.style.opacity=String(reveal);labelInner.style.transform=`translateY(${(1-reveal)*13}px) scale(${.9+reveal*.1}) rotate(${tilt}deg)`;renderer.render(scene,camera);labelRenderer.render(scene,camera);};animate(last);
    return()=>{if(hoverTimer)clearTimeout(hoverTimer);cancelAnimationFrame(frame);observer.disconnect();controls.dispose();renderer.dispose();textures.surface.dispose();textures.clouds.dispose();textures.hover.dispose();themedSurface.dispose();originalSurface.dispose();sphereGeometry.dispose();starGeometry.dispose();host.replaceChildren();};
  },[]);
  return <div className="three-globe-host" ref={hostRef} aria-label="Three.js 三维探索星球"/>;
}
