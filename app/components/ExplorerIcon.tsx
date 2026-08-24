type IconName = "arrow" | "book" | "close" | "compass" | "headphones" | "journal" | "map" | "shell" | "spark" | "waves";

export default function ExplorerIcon({name,size=20}:{name:IconName;size?:number}) {
  const common = {width:size,height:size,viewBox:"0 0 24 24",fill:"none","aria-hidden":true} as const;
  if(name==="arrow") return <svg {...common}><path d="M5 12h13m-5-5 5 5-5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>;
  if(name==="book") return <svg {...common}><path d="M4 5.5c2.7-.8 5.4-.2 8 1.5v12c-2.6-1.7-5.3-2.3-8-1.5v-12Zm16 0c-2.7-.8-5.4-.2-8 1.5v12c2.6-1.7 5.3-2.3 8-1.5v-12Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/></svg>;
  if(name==="close") return <svg {...common}><path d="m6 6 12 12M18 6 6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>;
  if(name==="compass") return <svg {...common}><circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.7"/><path d="m15.7 8.3-2 5.4-5.4 2 2-5.4 5.4-2Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/></svg>;
  if(name==="headphones") return <svg {...common}><path d="M4.5 13v-1a7.5 7.5 0 0 1 15 0v1M4.5 13H7v6H5.8c-.7 0-1.3-.6-1.3-1.3V13Zm15 0H17v6h1.2c.7 0 1.3-.6 1.3-1.3V13Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/></svg>;
  if(name==="journal") return <svg {...common}><path d="M6 4.5h11.5v15H6a2 2 0 0 1-2-2v-11a2 2 0 0 1 2-2Z" stroke="currentColor" strokeWidth="1.7"/><path d="M8 8h6M8 12h6M8 16h4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>;
  if(name==="map") return <svg {...common}><path d="m4 6 5-2 6 2 5-2v14l-5 2-6-2-5 2V6Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/><path d="M9 4v14M15 6v14" stroke="currentColor" strokeWidth="1.7"/></svg>;
  if(name==="shell") return <svg {...common}><path d="M4 16.5c0-6.7 3.2-11 8-11s8 4.3 8 11H4Z" stroke="currentColor" strokeWidth="1.7"/><path d="m12 6-3 10.5m3-10.5 3 10.5M6.5 9l3.2 7.5M17.5 9l-3.2 7.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>;
  if(name==="waves") return <svg {...common}><path d="M3 8c2.2 0 2.2 1.8 4.4 1.8S9.6 8 11.8 8s2.2 1.8 4.4 1.8S18.4 8 20.6 8M3 13c2.2 0 2.2 1.8 4.4 1.8s2.2-1.8 4.4-1.8 2.2 1.8 4.4 1.8 2.2-1.8 4.4-1.8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>;
  return <svg {...common}><path d="M12 2.8c.8 5.1 2.8 7.4 7.8 8.2-5 .8-7 3.1-7.8 8.2-.8-5.1-2.8-7.4-7.8-8.2 5-.8 7-3.1 7.8-8.2Z" fill="currentColor"/></svg>;
}
