import React from "react";
/** Label/value definition list (application detail). Empty values render "—". Optional muted icon per label. */
export function FieldList({items=[],style}){
  return(<dl style={{display:"grid",gridTemplateColumns:"max-content 1fr",rowGap:12,columnGap:24,margin:0,alignItems:"center",...style}}>
    {items.map(it=><React.Fragment key={it.label}><dt style={{color:"var(--text-secondary)",display:"flex",alignItems:"center",gap:8}}>{it.icon&&<span className="material-icons-outlined" aria-hidden="true" style={{fontSize:18,width:18,overflow:"hidden"}}>{it.icon}</span>}{it.label}</dt><dd style={{margin:0,minWidth:0,overflowWrap:"anywhere",color:"var(--text-primary)"}}>{it.value||"—"}</dd></React.Fragment>)}
  </dl>);
}
