"use client";

import {useEffect,useRef,useState} from "react";

const SETTINGS_KEY="ai-bole.platform-music.v1";

export default function PlatformMusicPlayer(){
  const audioRef=useRef<HTMLAudioElement|null>(null);
  const firstSyncRef=useRef(true);
  const [enabled,setEnabled]=useState(false);
  const [volume,setVolume]=useState(.28);
  const [open,setOpen]=useState(false);

  useEffect(()=>{
    try{const saved=JSON.parse(localStorage.getItem(SETTINGS_KEY)||"null");if(saved){setEnabled(Boolean(saved.enabled));setVolume(typeof saved.volume==="number"?saved.volume:.28)}}catch{}
  },[]);

  useEffect(()=>{
    if(firstSyncRef.current){firstSyncRef.current=false;return}
    const audio=audioRef.current;if(!audio)return;audio.volume=volume;
    localStorage.setItem(SETTINGS_KEY,JSON.stringify({enabled,volume}));
    if(enabled){audio.play().catch(()=>setEnabled(false))}else audio.pause();
  },[enabled,volume]);

  return <aside className={`platform-music ${open?"is-open":""}`} aria-label="探索背景音乐">
    <audio ref={audioRef} src="/audio/exploration-theme.ogg" loop preload="metadata"/>
    <button className={`platform-music-toggle ${enabled?"is-playing":""}`} type="button" aria-pressed={enabled} aria-label={enabled?"暂停背景音乐":"播放背景音乐"} onClick={()=>setEnabled(value=>!value)}>
      <span className="platform-music-mascot" aria-hidden="true"><i className="platform-music-eye eye-left"/><i className="platform-music-eye eye-right"/><i className="platform-music-smile"/><em>♪</em></span>
      <span className="platform-music-copy"><b>星星唱机</b><small>{enabled?"正在唱歌啦":"点击唤醒音乐"}</small></span>
    </button>
    <button className="platform-music-settings" type="button" aria-label={open?"收起音乐设置":"展开音乐设置"} aria-expanded={open} onClick={()=>setOpen(value=>!value)}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h10M18 8h2M4 16h2M10 16h10"/><circle cx="16" cy="8" r="2"/><circle cx="8" cy="16" r="2"/></svg>
    </button>
    <div className="platform-music-panel">
      <label htmlFor="platform-music-volume">背景音乐 <b>{Math.round(volume*100)}%</b></label>
      <input id="platform-music-volume" type="range" min="0" max="1" step="0.05" value={volume} onChange={event=>setVolume(Number(event.target.value))}/>
      <small>让音乐陪你探索每一座奇妙大陆</small>
    </div>
  </aside>;
}
