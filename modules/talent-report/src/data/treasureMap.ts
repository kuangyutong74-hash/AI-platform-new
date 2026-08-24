export type StarState = { discovered:string[]; order:string[] };
export type MapPosition = { x:number; y:number };

export const STAR_STATE_KEY="ai-bole-treasure-stars";

export const mapCopy={
  tag:"睡前故事时间",
  title:"你的天赋藏宝图",
  subtitle:"四块大陆上，藏着六颗属于你的星星 · 找到它们，点亮它们",
  sealHover:"这里藏着一颗星星，快来找我呀！",
  foundBurst:(name:string)=>`哇！你找到了「${name}」！`,
  progress:(n:number)=>`已点亮 ${n} / 6 颗星`,
  progressAria:(n:number)=>`已点亮 ${n} 颗，共 6 颗`,
  progressHint:"点亮全部星星，就能召唤你的完整天赋报告",
  celebrateTitle:"你的天赋星图完整点亮啦！",
  celebrateSub:"六颗星都找到了，和爸爸妈妈一起看看星星背后的故事吧",
  celebratePrimary:"和爸爸妈妈一起看完整报告 →",
  celebrateSecondary:"再逛一逛",
  revisit:"星星们都亮着，等你回来逛一逛",
  empty:"这张藏宝图还在路上，先去玩一会儿吧",
  collected:"收下它",
  source:(continent:string)=>`来自${continent}`,
  order:(n:number)=>`第 ${n} 颗找到的星星`,
  visit:(continent:string)=>`去${continent}探险 →`,
  back:"← 回到探索星球",
};

export const starConfessions:Record<string,string>={
  linguistic:"你让迷路的小星星找到了家。你脑袋里的小世界，我最爱听。",
  logical:"水管没接上，你没有放弃——转一转，就通了。再难的谜题，你都再试一次。",
  spatial:"你会在脑子里先搭一遍，再动手摆好。你是有耐心的小小建造师。",
  interpersonal:"你听得到别人心里在想什么，还想办法让大家都开心。好温柔的本事。",
  naturalistic:"\"这只的触角弯弯的，那只是直的！\"大自然的小秘密，逃不过你的眼睛。",
  intrapersonal:"你会说\"这个结局不像我想要的\"。懂得自己的心，是很厉害的本事。",
};

export const continentHints:Record<string,string>={
  想象之洲:"故事在这块大陆上发芽",
  创造之洲:"动手搭，动手造，谜题在等你",
  倾听之洲:"静下来，听一听身边的声音",
  未来之洲:"长大以后想做什么？",
};

export const starPositions:Record<string,MapPosition>={
  linguistic:{x:16,y:24},logical:{x:74,y:18},spatial:{x:58,y:32},
  interpersonal:{x:20,y:66},naturalistic:{x:34,y:74},intrapersonal:{x:78,y:68},
};

export const stickerByKey:Record<string,string>={
  linguistic:"/assets/storybook/talent-storybook.png",logical:"/assets/storybook/talent-puzzle.png",
  spatial:"/assets/storybook/talent-blocks.png",interpersonal:"/assets/storybook/talent-friends.png",
  intrapersonal:"/assets/storybook/talent-mirror.png",naturalistic:"/assets/storybook/talent-leaf.png",
};

export const continentRegions=[
  {name:"想象之洲",icon:"🌙",tone:"imagination",x:5,y:7,w:41,h:39},
  {name:"创造之洲",icon:"🏗️",tone:"creation",x:51,y:6,w:43,h:40},
  {name:"倾听之洲",icon:"💬",tone:"listening",x:5,y:50,w:43,h:42},
  {name:"未来之洲",icon:"🚀",tone:"future",x:52,y:51,w:42,h:40},
] as const;

export const starAria={
  sealed:(name:string,continent:string)=>`找到「${name}」——${continent}的星星`,
  lit:(name:string)=>`查看「${name}」的故事`,
};

export function loadStarState(validKeys:string[]):StarState{
  try{
    const raw=localStorage.getItem(STAR_STATE_KEY);if(!raw)return {discovered:[],order:[]};
    const parsed=JSON.parse(raw) as Partial<StarState>;
    const discovered=(Array.isArray(parsed.discovered)?parsed.discovered:[]).filter(key=>validKeys.includes(key));
    const order=(Array.isArray(parsed.order)?parsed.order:[]).filter((key,index,list)=>discovered.includes(key)&&list.indexOf(key)===index);
    return {discovered:[...new Set(discovered)],order:[...order,...discovered.filter(key=>!order.includes(key))]};
  }catch{return {discovered:[],order:[]}}
}

export function saveStarState(state:StarState){localStorage.setItem(STAR_STATE_KEY,JSON.stringify(state))}
