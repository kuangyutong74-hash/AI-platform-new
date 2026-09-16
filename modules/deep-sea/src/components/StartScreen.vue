<template>
  <div class="start-screen">
    <!--
      THESIS: 一张正在发生的动画电影海报，让孩子进入救援故事，而不是阅读控制台。
      OWN-WORLD: 深海蓝、珊瑚橙与珍珠白；电影光束、圆润角色、发光基地和海水景深。
      STORY: 风暴后的基地等待修复，沫沫带队出发，孩子一键加入三段重建旅程。
      FIRST VIEWPORT: 全幅场景占满画面，左侧大标题与主行动，右下任务航线顺着基地延伸。
      FORM: 用户指定的高品质家庭动画电影封面；精准窄范围重设计，无方向种子。
      FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
    -->
    <img class="cover-art" :src="coverArt" alt="风暴后的蔚蓝深海基地，沫沫带着海洋伙伴准备出发重建" />
    <div class="cover-shade" aria-hidden="true"></div>
    <StartEffects />

    <div class="cover-content">
      <section class="cover-copy">
        <div class="call-signal">
          <span aria-hidden="true"></span>
          <span v-html="p('沫沫正在呼叫小队长')"></span>
        </div>

        <h1 class="start-title">
          <span v-html="p('蔚蓝深海基地')"></span>
          <strong v-html="p('重建计划')"></strong>
        </h1>

        <p class="hero-story" v-html="p('风暴刚刚离开，珊瑚公寓、电力管网和海洋议事厅都在等你。和沫沫一起，让基地重新发光！')"></p>

        <div class="cover-actions">
          <button @mouseenter="playHover" @click="startGame" class="start-cta">
            <span v-html="p('出发，开始重建')"></span>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h13m-5-5 5 5-5 5" /></svg>
          </button>
          <p><b>约 15 分钟</b><span>观察 · 规划 · 沟通</span></p>
        </div>
      </section>

      <section class="mission-route" aria-label="三项基地重建任务">
        <header>
          <span v-html="p('今天的重建路线')"></span>
          <small>完成三项任务，点亮守护者勋章</small>
        </header>
        <ol>
          <li v-for="(mission, i) in missions" :key="mission.title">
            <span class="route-number">{{ i + 1 }}</span>
            <img :src="mission.iconSrc" alt="" />
            <div><b v-html="p(mission.title)"></b><small v-html="p(mission.desc)"></small></div>
          </li>
        </ol>
      </section>
    </div>
  </div>
</template>

<script setup>
import { playHover } from '../utils/sounds.js'
import { usePinyinText } from '../utils/pinyin.js'
import StartEffects from './effects/StartEffects.vue'
import coverArt from '../assets/generated/deep-sea-cover-cinematic-v1.webp'
import coralApartmentIcon from '../assets/generated/nav/nav-coral-apartment.png'
import currentGridIcon from '../assets/generated/nav/nav-current-grid.png'
import mediationIcon from '../assets/generated/nav/nav-mediation.png'

const { p } = usePinyinText()
const emit = defineEmits(['go-level'])
const startGame = () => emit('go-level', 'LEVEL_1')

const missions = [
  { iconSrc: coralApartmentIcon, title: '珊瑚公寓', desc: '观察伙伴，帮大家找到新家' },
  { iconSrc: currentGridIcon, title: '洋流电网', desc: '铺好管线，让能源重新流动' },
  { iconSrc: mediationIcon, title: '海洋议事厅', desc: '听懂伙伴，帮助大家和好' },
]
</script>

<style scoped>
.start-screen{position:relative;height:100%;min-height:0;overflow:hidden;background:#031b39;color:#fff;isolation:isolate}
.cover-art{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 54%;filter:saturate(1.06) contrast(1.03);transform:scale(1.01)}
.cover-shade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(2,15,39,.94) 0%,rgba(2,20,48,.79) 29%,rgba(4,30,57,.2) 56%,rgba(4,22,44,.12) 72%),linear-gradient(0deg,rgba(1,12,31,.83) 0%,transparent 35%,rgba(1,17,42,.1) 70%);z-index:1}
.cover-content{position:relative;z-index:12;height:100%;display:grid;grid-template-columns:minmax(0,650px);align-content:center;align-items:start;gap:26px;padding:clamp(30px,5vw,76px)}
.cover-copy{align-self:center;max-width:650px;padding-top:2vh}
.call-signal{display:inline-flex;align-items:center;gap:9px;margin-bottom:18px;padding:7px 13px;border-radius:999px;background:rgba(5,34,66,.72);box-shadow:0 8px 22px rgba(0,10,30,.24);color:#bff5ff;font-size:clamp(12px,1.1vw,15px);font-weight:800;letter-spacing:.06em;backdrop-filter:blur(8px)}
.call-signal>span:first-child{width:9px;height:9px;border-radius:50%;background:#ffcc70;box-shadow:0 0 0 5px rgba(255,204,112,.15),0 0 18px rgba(255,204,112,.7);animation:signalPulse 2.2s ease-in-out infinite}
.start-title{margin:0;color:#fff;font-family:'Microsoft YaHei UI','PingFang SC','Noto Sans CJK SC',sans-serif;font-size:clamp(3.2rem,5.35vw,5.35rem);font-weight:900;line-height:1.02;letter-spacing:-.025em;text-wrap:balance;text-shadow:0 5px 24px rgba(0,8,28,.55)}
.start-title strong{display:block;margin-top:10px;color:#ffcf74;font:inherit;font-size:.62em;letter-spacing:.02em}
.hero-story{max-width:590px;margin:25px 0 0;color:#e5faff;font-size:clamp(15px,1.35vw,20px);font-weight:700;line-height:1.7;text-shadow:0 2px 12px rgba(0,9,27,.65)}
.cover-actions{display:flex;align-items:center;gap:20px;margin-top:30px}
.start-cta{display:inline-flex;min-height:58px;align-items:center;gap:20px;padding:14px 25px 14px 28px;border:0;border-radius:999px;background:#ff765f;color:#fff;font-size:clamp(16px,1.3vw,20px);font-weight:900;box-shadow:0 14px 30px rgba(92,22,16,.35),inset 0 1px rgba(255,255,255,.38);cursor:pointer;transition:transform .2s cubic-bezier(.2,.8,.2,1),box-shadow .2s ease,background .2s ease}
.start-cta svg{width:26px;height:26px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round;transition:transform .2s cubic-bezier(.2,.8,.2,1)}
.start-cta:hover{background:#ff876f;transform:translateY(-3px);box-shadow:0 19px 36px rgba(92,22,16,.42),inset 0 1px rgba(255,255,255,.45)}
.start-cta:hover svg{transform:translateX(4px)}
.start-cta:focus-visible{outline:3px solid #fff2bd;outline-offset:4px}
.cover-actions>p{display:grid;gap:2px;margin:0;color:#d9f7ff;font-size:12px;line-height:1.45;text-shadow:0 2px 8px rgba(0,8,28,.55)}
.cover-actions>p b{color:#fff;font-size:14px}.cover-actions>p span{opacity:.84}
.mission-route{justify-self:start;width:min(100%,650px);padding:17px 19px 18px;border-radius:16px;background:rgba(3,27,57,.82);box-shadow:0 20px 42px rgba(0,10,28,.33);backdrop-filter:blur(12px) saturate(1.1)}
.mission-route header{display:flex;align-items:end;justify-content:space-between;gap:16px;padding:0 2px 13px}.mission-route header>span{font-size:17px;font-weight:900}.mission-route header small{color:#b9eafa;font-size:11px}
.mission-route ol{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:0;padding:0;list-style:none}
.mission-route li{position:relative;display:grid;grid-template-columns:46px 1fr;align-items:center;gap:9px;min-width:0;padding:10px;border-radius:13px;background:rgba(239,252,255,.12);box-shadow:inset 0 1px rgba(255,255,255,.12)}
.mission-route li img{width:46px;height:46px;border-radius:12px;object-fit:cover}.mission-route li div{display:grid;gap:3px;min-width:0}.mission-route li b{font-size:13px}.mission-route li small{color:#c8ecf5;font-size:10px;line-height:1.45}
.route-number{position:absolute;top:-7px;right:8px;display:grid;width:21px;height:21px;place-items:center;border-radius:50%;background:#ffcf74;color:#193451;font-size:11px;font-weight:900;box-shadow:0 5px 12px rgba(0,10,28,.3)}
@keyframes signalPulse{0%,100%{transform:scale(.88);opacity:.76}50%{transform:scale(1);opacity:1}}
@media(max-width:1023px){.cover-content{grid-template-columns:minmax(0,620px);align-content:end;gap:24px;padding:clamp(26px,6vw,54px)}.cover-copy{align-self:end;max-width:620px}.mission-route{justify-self:start}.cover-art{object-position:62% center}.cover-shade{background:linear-gradient(90deg,rgba(2,15,39,.91),rgba(2,20,48,.5) 62%,rgba(4,22,44,.14)),linear-gradient(0deg,rgba(1,12,31,.88),transparent 54%)}}
@media(max-width:640px){.cover-content{gap:18px;width:100%;min-width:0;padding:24px 18px 20px}.cover-copy{width:100%;min-width:0;max-width:100%;padding:0}.call-signal{max-width:100%;margin-bottom:12px}.start-title{max-width:100%;font-size:clamp(2.2rem,10.5vw,3rem);letter-spacing:-.05em;white-space:normal;overflow-wrap:anywhere}.start-title strong{white-space:normal}.hero-story{max-width:100%;margin-top:16px;font-size:14px;line-height:1.55;white-space:normal;overflow-wrap:anywhere}.cover-actions{margin-top:20px}.start-cta{min-height:52px;padding:12px 20px;font-size:16px}.cover-actions>p{display:none}.mission-route{width:100%;min-width:0;max-width:100%;padding:14px}.mission-route header{padding-bottom:10px}.mission-route header small{display:none}.mission-route ol{grid-template-columns:minmax(0,1fr);gap:7px}.mission-route li{grid-template-columns:38px minmax(0,1fr);padding:7px 9px}.mission-route li img{width:38px;height:38px}.mission-route li small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.cover-art{object-position:68% center;transform:scale(1.06)}.cover-shade{background:linear-gradient(90deg,rgba(2,15,39,.9),rgba(2,20,48,.36)),linear-gradient(0deg,rgba(1,12,31,.92),rgba(1,12,31,.22) 66%)}}
@media(max-height:720px) and (min-width:641px){.cover-content{padding-block:24px}.start-title{font-size:clamp(3rem,5vw,4.6rem)}.hero-story{margin-top:16px}.cover-actions{margin-top:20px}.mission-route{padding:14px 16px}.mission-route header{padding-bottom:9px}}
@media(prefers-reduced-motion:reduce){.call-signal>span:first-child,.start-cta,.start-cta svg{animation:none;transition:none}}
</style>
