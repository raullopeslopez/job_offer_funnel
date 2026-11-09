import React from "react";
/** h4 page title that grows, with page actions aligned right (outlined secondary first, contained primary last). */
export function PageHeader({title,actions,eyebrow,style}){
  return(<div style={{display:"flex",alignItems:"center",flexWrap:"wrap",columnGap:16,rowGap:12,marginBottom:16,...style}}>
    {eyebrow&&<div style={{flexBasis:"100%",marginBottom:-8}}>{eyebrow}</div>}
    <h1 style={{flex:"1 1 auto",minWidth:"min(100%, 240px)",margin:0,fontFamily:"var(--font-heading)",fontSize:"var(--h4-size)",fontWeight:"var(--h4-weight)",lineHeight:"var(--h4-line)",letterSpacing:"var(--h4-tracking)"}}>{title}</h1>
    {actions&&<div style={{display:"flex",gap:8,flexWrap:"wrap"}}>{actions}</div>}
  </div>);
}
