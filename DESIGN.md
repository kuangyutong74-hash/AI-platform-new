---
name: AI 伯乐儿童天赋探索星球
description: 用温暖的水彩星球与成长手账，陪低年级孩子看见每一次认真尝试。
colors:
  starry-indigo: "#21183d"
  deep-night: "#172342"
  parchment-cream: "#fff8e8"
  ink-plum: "#40374e"
  starlight-gold: "#f0cb70"
  peach-warmth: "#f8e4e5"
  watercolor-blue: "#dcebf0"
  quiet-text: "#5f5562"
typography:
  display:
    fontFamily: "Ma Shan Zheng, ZCOOL KuaiLe, cursive"
    fontSize: "clamp(2.5rem, 5vw, 4.35rem)"
    fontWeight: 400
    lineHeight: 1.02
  body:
    fontFamily: "LXGW WenKai, STKaiti, KaiTi, Microsoft YaHei, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "LXGW WenKai, Microsoft YaHei, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 700
    lineHeight: 1.45
rounded:
  pill: "999px"
  soft: "18px"
  paper: "48% 52% 49% 51% / 8% 10% 9% 11%"
spacing:
  xs: "8px"
  sm: "12px"
  md: "18px"
  lg: "28px"
  xl: "44px"
components:
  button-gold:
    backgroundColor: "{colors.starlight-gold}"
    textColor: "{colors.ink-plum}"
    rounded: "{rounded.pill}"
    padding: "10px 18px"
    height: "48px"
  card-paper:
    backgroundColor: "{colors.parchment-cream}"
    textColor: "{colors.ink-plum}"
    rounded: "{rounded.paper}"
    padding: "28px"
---

# Design System: AI 伯乐儿童天赋探索星球

## Overview

**Creative North Star: “水彩星球成长手账”**

界面像孩子亲手翻开的星空剪贴簿：深靛蓝水彩天空提供安静的想象空间，奶油纸张承载需要阅读和操作的内容，星光金只在行动、进度和鼓励时出现。画面温暖、手作、从容，不追求科技炫技；每一页先让孩子看懂图，再读懂一句话，最后完成一个明确动作。

页面可以有童话感，但信息必须诚实、清楚、可预测。真实记录优先；没有真实数据时，示例必须明确标注。拒绝通用 SaaS 仪表盘和霓虹科幻界面。

**Key Characteristics:**

- 水彩星空、纸张肌理与剪贴簿式层叠。
- 低年级儿童能读懂的短句、大标题和大触控目标。
- 四座探索大陆地位平等，以色调和插画区分。
- 温和的漂浮、翻页和聚焦反馈，不用喧闹动画。

## Colors

颜色以星夜靛蓝和羊皮纸奶油色建立“探索—阅读”的层次，金色负责稀少而明确的鼓励信号。

### Primary

- **星夜靛蓝：** 页面天空、个人页顶栏与移动底栏的主背景。
- **深海夜蓝：** 成长星路的深层背景与遮罩。

### Secondary

- **星光金：** 活跃导航、主按钮、进度与星星提示；不可铺满大面积正文。
- **桃粉暖光：** 想象之洲标签、胶带和温柔提示。
- **水彩浅蓝：** 深海与倾听相关的场景标签。

### Neutral

- **羊皮纸奶油：** 阅读卡片、手账、对话框和高对比信息面。
- **墨梅正文：** 纸张上的标题与正文。
- **安静小字：** 纸张上的日期、状态和辅助信息，仍需满足可读对比度。

**The Paper Contrast Rule.** 长文本只放在浅色纸张上；星空背景只承载短标题、标签或带阴影的引导句。

## Typography

**Display Font:** Ma Shan Zheng，回退到 ZCOOL KuaiLe 与通用手写字体。  
**Body Font:** LXGW WenKai，回退到楷体、微软雅黑和无衬线字体。

**Character:** 标题像孩子的手写旅行题签，正文像清楚温和的成长手账。标题有想象力，正文始终以易读为先。

### Hierarchy

- **Display**（400，响应式大字号，紧凑行高）：页面主标题和故事书标题。
- **Headline**（400，约 2.4–3.7rem）：作品名、里程碑名和章节题签。
- **Body**（400，约 1rem，1.7–1.9 行高）：说明、作品内容和成长纸条。
- **Label**（700，约 13px）：状态、岛屿名和主要按钮短语。

**The One-Sentence Rule.** 儿童第一眼看到的引导不超过一句；需要更多解释时分成卡片正文。

## Layout

桌面端使用居中的宽容器和不对称纸张/插画构图；作品页以代码绘制的打开书页承载四枚透明立体贴纸，贴纸本体不得带截图式矩形底板，文字只落在独立的小便签上。成长页沿单条星光路径交替布置从注册日开始的模块使用里程碑。核心容器通常保留 34–44px 外侧留白。

850px 以下顶栏导航固定到视口底部；600px 以下改为单列，按钮保持至少 42–48px 高。移动端始终为底栏预留安全空间，首屏需要同时露出页面身份、简短说明和下一段内容的起点。

## Elevation & Depth

深度来自水彩背景、纸张纹理、半透明胶带和柔和环境阴影的组合。纸张卡片使用宽而低对比的阴影，悬停只轻微上移；对话框可增加深色遮罩，但不使用硬朗边框或霓虹光晕。

**The Layered Paper Rule.** 阴影用于解释纸张层级和可点击性，而不是装饰所有元素。

## Shapes

纸张和岛屿采用略微不规则的椭圆角、裁切角与轻微旋转，避免机械化的统一圆角。操作按钮使用完整胶囊形，头像和编号使用手绘式近圆形。需要阅读的正文面保持稳定轮廓，不让形状妨碍排版。

## Components

### Buttons

- **Shape:** 主操作为胶囊形，最小高度 48px；文字动作可以用清晰下划线式底边。
- **Primary:** 星光金底、墨梅文字；一屏只保留一个最强主操作。
- **Hover / Focus:** 轻微位移或间距变化；键盘聚焦统一使用 3px 高对比浅金外环与 3px 偏移。
- **Secondary:** 半透明纸张底或细描边，不能比主按钮更抢眼。

### Cards / Containers

- **Corner Style:** 轻微不规则纸张轮廓，允许小角度旋转。
- **Background:** 羊皮纸奶油色叠加真实水彩纸纹理。
- **Shadow Strategy:** 柔和环境阴影表达前后层级。
- **Internal Padding:** 手机约 22–28px，桌面约 40–55px。

### Navigation

桌面为深靛蓝顶栏中的短文字导航，活跃项使用星光金底边。手机端保留品牌顶栏，四个核心入口固定在深色底栏，当前页用金色文字与底边双重标记。

### Treasure Stickers and Milestones

宝藏贴纸先呈现场景插画，再显示收藏类别和数量；四类必须等宽等权。成长里程碑使用可点击水彩岛屿、顺序编号、日期和明确的“打开/点亮”动作；未解锁状态仍告诉孩子下一步该做什么。

## Do's and Don'ts

### Do:

- **Do** 用真实数据生成作品与成长记录；空数据时明确写“示例”。
- **Do** 保持四个探索模块同等视觉权重。
- **Do** 为键盘操作、朗读、放大文字、对话框关闭和返回路径提供清晰反馈。
- **Do** 优先使用压缩 WebP，并延迟加载首屏外插画。

### Don't:

- **Don't** 使用通用后台表格、密集指标卡或排行榜来呈现儿童成长。
- **Don't** 用霓虹渐变、强玻璃拟态或快速闪烁替代温和的水彩手作感。
- **Don't** 把示例内容伪装成孩子的真实记录。
- **Don't** 让固定导航遮住正文、按钮或成长路径的起点。
