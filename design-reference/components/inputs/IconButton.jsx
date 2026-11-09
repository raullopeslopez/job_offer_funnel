import React from "react";
/** Icon-only button (Material Icons Outlined glyph). Always pass a label. */
export function IconButton({icon,label,onClick,size="medium",disabled,style}){
  const[h,setH]=React.useState(false);const s=size==="small"?32:40;
  return <button aria-label={label} title={label} disabled={disabled} onClick={onClick} onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)} style={{width:s,height:s,flexShrink:0,borderRadius:"var(--icon-button-radius)",border:0,display:"grid",placeItems:"center",cursor:disabled?"default":"pointer",background:h&&!disabled?"var(--action-hover)":"transparent",color:disabled?"var(--text-disabled)":"var(--action-active)",transition:"background-color 150ms var(--ease-standard)",...style}}><span className="material-icons-outlined" style={{fontSize:size==="small"?20:24}}>{icon}</span></button>;
}
