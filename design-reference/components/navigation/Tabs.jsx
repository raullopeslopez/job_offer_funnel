import React from "react";
/** Underlined tabs with a 2px primary indicator. */
export function Tabs({value,onChange,tabs=[],style}){
  return(<div role="tablist" style={{display:"flex",borderBottom:"1px solid var(--divider)",minHeight:"var(--tab-height)",...style}}>
    {tabs.map(t=><Tab key={t.value} active={t.value===value} onClick={()=>onChange&&onChange(t.value)}>{t.label}</Tab>)}
  </div>);
}
function Tab({active,onClick,children}){
  return <button role="tab" aria-selected={active} onClick={onClick} style={{position:"relative",minWidth:72,maxWidth:360,minHeight:"var(--tab-height)",padding:"12px 16px",border:0,background:"transparent",cursor:"pointer",fontFamily:"var(--font-family)",fontSize:"var(--button-size)",fontWeight:500,lineHeight:1.25,letterSpacing:"var(--tab-tracking)",textTransform:"var(--tab-transform)",color:active?"var(--primary-main)":"var(--text-secondary)",marginBottom:-1}}>
    {children}{active&&<span style={{position:"absolute",left:0,right:0,bottom:0,height:2,background:"var(--primary-main)"}}/>}
  </button>;
}
