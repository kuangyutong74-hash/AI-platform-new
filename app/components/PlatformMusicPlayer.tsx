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
      <svg viewBox="0 0 32 32" aria-hidden="true"><path d="M12 23.5a4 4 0 1 1-2.1-3.52V9.2l14-3v13.3a4 4 0 1 1-2.1-3.52V10.4L12 12.5v11Z"/></svg>
      <span>{enabled?"音乐播放中":"开启音乐"}</span>
    </button>
    <button className="platform-music-settings" type="button" aria-label={open?"收起音乐设置":"展开音乐设置"} aria-expanded={open} onClick={()=>setOpen(value=>!value)}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h10M18 8h2M4 16h2M10 16h10"/><circle cx="16" cy="8" r="2"/><circle cx="8" cy="16" r="2"/></svg>
    </button>
    <div className="platform-music-panel">
      <label htmlFor="platform-music-volume">背景音乐 <b>{Math.round(volume*100)}%</b></label>
      <input id="platform-music-volume" type="range" min="0" max="1" step="0.05" value={volume} onChange={event=>setVolume(Number(event.target.value))}/>
      <small>在探索星球、我的作品和天赋藏宝图间切换时会继续播放</small>
    </div>
  </aside>;
}
