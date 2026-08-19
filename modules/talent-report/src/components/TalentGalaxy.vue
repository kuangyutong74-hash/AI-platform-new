<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import * as THREE from "three";
import type { Talent } from "../data/mockReport";

const props = defineProps<{ talents: Talent[]; activeTalentKey?: string }>();
const emit = defineEmits<{ select: [Talent] }>();
const host = ref<HTMLDivElement>();
let renderer: THREE.WebGLRenderer | undefined;
let resizeObserver: ResizeObserver | undefined;
let animationFrame = 0;

onMounted(() => {
  if (!host.value) return;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  camera.position.set(0, 0, 11.8);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, premultipliedAlpha: false, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.6));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  host.value.appendChild(renderer.domElement);

  // 共用程序化星云材质：球面明暗与Fresnel边缘共同建立立体感，无镜面高光。
  const createNebulaMaterial = (color: string, seed: number, opacity = 1) => new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { time: { value: 0 }, tint: { value: new THREE.Color(color) }, seed: { value: seed }, alpha: { value: opacity } },
    vertexShader: `varying vec2 vUv;varying vec3 vN;varying vec3 vV;void main(){vUv=uv;vec4 mv=modelViewMatrix*vec4(position,1.);vV=-mv.xyz;vN=normalize(normalMatrix*normal);gl_Position=projectionMatrix*mv;}`,
    fragmentShader: `
      uniform float time;uniform vec3 tint;uniform float seed;uniform float alpha;varying vec2 vUv;varying vec3 vN;varying vec3 vV;
      float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7))+seed)*43758.5453);}float n(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1)),f.x),f.y);}
      void main(){vec2 p=vUv*4.8+vec2(time*.035,-time*.022)+seed;float cloud=n(p)+.52*n(p*2.15+2.7);float facing=max(dot(normalize(vN),normalize(vV)),0.);float rim=pow(1.-facing,2.1);float core=smoothstep(.95,.35,length(vUv-vec2(.43,.56)));
      vec3 shadow=tint*.18;vec3 body=mix(shadow,tint*(.72+cloud*.55),facing*.78+.16);body+=vec3(.55,.78,1.)*rim*.72+vec3(.7,.86,1.)*core*.16;gl_FragColor=vec4(body,alpha*(.76+rim*.22));}
    `,
  });

  // 主球退居背景，仅作为星群的空间锚点。
  const coreMaterial = createNebulaMaterial("#6576bd", 9.2, 0.58);
  const core = new THREE.Mesh(new THREE.SphereGeometry(1.02, 56, 56), coreMaterial);
  core.scale.set(1, 0.96, 1); scene.add(core);
  const cloudMaterial = createNebulaMaterial("#86b6df", 16.4, 0.16);
  const coreClouds = new THREE.Mesh(new THREE.SphereGeometry(1.055, 48, 48), cloudMaterial);
  coreClouds.scale.set(1, 0.96, 1); scene.add(coreClouds);
  const coreGlow = new THREE.Mesh(new THREE.SphereGeometry(1.12, 40, 40), new THREE.ShaderMaterial({
    transparent: true, side: THREE.BackSide, blending: THREE.AdditiveBlending, depthWrite: false,
    vertexShader: "varying vec3 n;void main(){n=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}",
    fragmentShader: "varying vec3 n;void main(){float a=pow(1.-abs(n.z),2.4);gl_FragColor=vec4(.25,.48,.9,a*.15);}",
  })); scene.add(coreGlow);
  const coreRing = new THREE.Mesh(
    new THREE.RingGeometry(1.26, 1.285, 96),
    new THREE.MeshBasicMaterial({ color: 0x9da9ef, transparent: true, opacity: 0.16, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false }),
  );
  coreRing.rotation.set(1.18, 0.08, -0.22); scene.add(coreRing);

  // 页面内星尘保持和封面同一紫蓝底色，不再产生独立黑色画布区。
  const dustGeometry = new THREE.BufferGeometry();
  const dustPositions: number[] = [];
  for (let i = 0; i < 430; i += 1) dustPositions.push((Math.random() - 0.5) * 18, (Math.random() - 0.5) * 9.5, (Math.random() - 0.5) * 7);
  dustGeometry.setAttribute("position", new THREE.Float32BufferAttribute(dustPositions, 3));
  const dust = new THREE.Points(dustGeometry, new THREE.PointsMaterial({ color: 0xc8d8ff, size: 0.025, transparent: true, opacity: 0.48, depthWrite: false, blending: THREE.AdditiveBlending }));
  scene.add(dust);

  // 画面下半圈就是镜头前方：y越低，z越靠近相机，近大远小符合观看直觉。
  // 拉开椭圆的纵向间距，配合更克制的远近缩放，让六颗星在画面中保持均衡呼吸感。
  const orbitPoint = (angle: number) => new THREE.Vector3(Math.cos(angle) * 4.15, Math.sin(angle) * 2.38, -Math.sin(angle) * 1.55).applyAxisAngle(new THREE.Vector3(0, 0, 1), -0.1);
  for (let i = 0; i < 112; i += 2) {
    if (i > 82 && i < 96) continue;
    const p1 = orbitPoint(i / 112 * Math.PI * 2), p2 = orbitPoint((i + 1) / 112 * Math.PI * 2);
    const depth = THREE.MathUtils.clamp((p1.z + 1.55) / 3.1, 0, 1);
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([p1, p2]), new THREE.LineBasicMaterial({ color: 0xa998eb, transparent: true, opacity: 0.02 + depth * 0.15, blending: THREE.AdditiveBlending, depthWrite: false }));
    scene.add(line);
  }

  const atlas = new THREE.TextureLoader().load("/assets/talent-nebula-satellites-v1.png"); atlas.colorSpace = THREE.SRGBColorSpace;
  const groups: THREE.Group[] = [], hitTargets: THREE.Mesh[] = [], labels: HTMLButtonElement[] = [], satelliteMaterials: THREE.ShaderMaterial[] = [];
  // 根据实际星星数量均分完整轨道，六颗星会以 60° 间隔环绕，不再沿左侧堆叠。
  const orbitStep = (Math.PI * 2) / Math.max(props.talents.length, 1);
  props.talents.forEach((talent, index) => {
    const group = new THREE.Group(); group.userData = { index, talent, angle: index * orbitStep };
    const material = createNebulaMaterial(talent.color, 1.7 + index * 2.13, 0.96); satelliteMaterials.push(material);
    const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.48, 48, 48), material); sphere.userData = { talent, group }; hitTargets.push(sphere); group.add(sphere);

    // 图像素材只作外层星云雾，不再承担卫星主体，因此保留柔软感同时拥有真实球体明暗。
    const texture = atlas.clone(); texture.needsUpdate = true; texture.repeat.set(0.25, 0.5); texture.offset.set((index % 4) * 0.25, index < 4 ? 0.5 : 0);
    const haze = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, color: new THREE.Color(talent.color), transparent: true, opacity: 0.38, depthWrite: false, blending: THREE.AdditiveBlending }));
    haze.scale.set(1.62, 1.62, 1); group.add(haze);
    groups.push(group); scene.add(group);

    const label = document.createElement("button"); label.type = "button"; label.className = "galaxy-label";
    label.innerHTML = `<span>${talent.icon}</span><b>${talent.childName}</b><small>${talent.continent}</small>`;
    label.setAttribute("aria-label", `查看${talent.childName}`); label.addEventListener("click", () => emit("select", talent));
    host.value!.appendChild(label); labels.push(label);
  });

  const raycaster = new THREE.Raycaster(), pointer = new THREE.Vector2(9, 9);
  const setPointer = (event: PointerEvent) => { const rect = renderer!.domElement.getBoundingClientRect(); pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -((event.clientY - rect.top) / rect.height * 2 - 1)); };
  renderer.domElement.addEventListener("pointermove", setPointer); renderer.domElement.addEventListener("pointerleave", () => pointer.set(9, 9));
  renderer.domElement.addEventListener("click", event => { setPointer(event); raycaster.setFromCamera(pointer, camera); const hit = raycaster.intersectObjects(hitTargets, false)[0]; if (hit) emit("select", hit.object.userData.talent); });

  const resize = () => { if (!host.value || !renderer) return; const width = host.value.clientWidth, height = host.value.clientHeight; renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix(); };
  resizeObserver = new ResizeObserver(resize); resizeObserver.observe(host.value); resize();
  const clock = new THREE.Clock(), projected = new THREE.Vector3();
  const animate = () => {
    animationFrame = requestAnimationFrame(animate); const time = clock.getElapsedTime();
    core.rotation.y = time * 0.025; coreMaterial.uniforms.time.value = time; coreClouds.rotation.y = -time * 0.045; coreClouds.rotation.z = time * 0.012; cloudMaterial.uniforms.time.value = time * 1.2; coreRing.rotation.z = -0.22 + Math.sin(time * 0.22) * 0.025; dust.rotation.z = time * 0.0025; dust.position.y = Math.sin(time * 0.15) * 0.08;
    groups.forEach((group, index) => {
      const angle = group.userData.angle + time * 0.052; const p = orbitPoint(angle); p.y += Math.sin(time * 0.9 + index * 1.8) * 0.1; group.position.copy(p);
      const depth = THREE.MathUtils.clamp((p.z + 1.55) / 3.1, 0, 1), pulse = 1 + Math.sin(time * (1.15 + index * 0.03) + index) * 0.065;
      const linked = props.activeTalentKey === group.userData.talent.key;
      const linkedFlicker = linked ? 1.12 + Math.sin(time * 11 + index) * 0.055 : 1;
      // 强化近大远小；DOM卡片联动时额外放大并产生轻微星光闪烁。
      group.scale.setScalar((0.72 + depth * 0.42) * pulse * linkedFlicker); satelliteMaterials[index].uniforms.time.value = time + index;
      group.children.forEach(child => { const material = (child as THREE.Mesh).material as THREE.Material & { opacity?: number }; if ("opacity" in material) material.opacity = child instanceof THREE.Sprite ? (0.12 + depth * 0.48) * (linked ? 1.55 : 1) : Math.min(1,(0.28 + depth * 0.7) * (linked ? 1.18 : 1)); });
      projected.copy(p).project(camera); const x = (projected.x * 0.5 + 0.5) * host.value!.clientWidth, y = (-projected.y * 0.5 + 0.5) * host.value!.clientHeight;
      const label = labels[index]; label.classList.toggle("linked",linked); label.style.left = `${x}px`; label.style.top = `${y + 30 + depth * 18}px`; label.style.opacity = `${Math.min(1,(0.24 + depth * 0.76) * (linked ? 1.2 : 1))}`; label.style.zIndex = `${10 + Math.round(depth * 10)}`; label.style.transform = `translate(-50%,0) scale(${(0.68 + depth * 0.34) * (linked ? 1.04 : 1)})`;
    });
    raycaster.setFromCamera(pointer, camera); const hovered = raycaster.intersectObjects(hitTargets, false)[0]?.object as THREE.Mesh | undefined;
    renderer!.domElement.style.cursor = hovered ? "pointer" : "default"; if (hovered) hovered.parent?.scale.multiplyScalar(1.1);
    renderer!.render(scene, camera);
  }; animate();
});

onBeforeUnmount(() => { cancelAnimationFrame(animationFrame); resizeObserver?.disconnect(); renderer?.dispose(); host.value?.querySelectorAll(".galaxy-label").forEach(label => label.remove()); renderer?.domElement.remove(); });
</script>

<template><div ref="host" class="talent-galaxy" aria-label="六颗立体天赋星沿星轨环绕；每颗星均显示名称并可点击查看"></div></template>
