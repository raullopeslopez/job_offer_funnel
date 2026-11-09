import React from "react";
/** Mobile top bar (< 900px): menu button, wordmark, trailing slot. Sticky, hairline bottom border. */
export function AppBar({title="Job Offer Funnel",leading,trailing,style}){
  return(<header style={{position:"sticky",top:0,zIndex:1100,height:56,display:"flex",alignItems:"center",gap:8,padding:"0 8px",background:"var(--appbar-bg)",borderBottom:"1px solid var(--divider)",color:"var(--text-primary)",...style}}>
    {leading}
    <div style={{flex:1,fontFamily:"var(--wordmark-font)",fontWeight:"var(--wordmark-weight)",fontSize:"1.125rem",letterSpacing:"var(--h6-tracking)",paddingLeft:leading?0:8}}>{title}</div>
    {trailing}
  </header>);
}
