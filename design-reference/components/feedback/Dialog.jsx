import React from "react";
/** Centered modal form: h6 title, content, right-aligned actions (Cancel + contained submit). */
export function Dialog({open=true,title,children,actions,onClose,inline=false,maxWidth=600}){
  if(!open)return null;
  const paper=(<div role="dialog" onClick={e=>e.stopPropagation()} style={{"--label-bg":"var(--bg-paper)",background:"var(--bg-paper)",borderRadius:"var(--radius-lg)",boxShadow:"var(--shadow-dialog)",width:inline?"100%":"calc(100% - 2 * clamp(16px, 4vw, 32px))",maxWidth,margin:inline?0:"clamp(16px, 4vw, 32px)",maxHeight:"calc(100% - 2 * clamp(16px, 4vw, 32px))",display:"flex",flexDirection:"column",overflowY:"auto",color:"var(--text-primary)"}}>
    {title&&<h2 style={{margin:0,padding:"16px 24px",fontFamily:"var(--font-heading)",fontSize:"var(--h6-size)",fontWeight:"var(--h6-weight, 500)",lineHeight:"var(--h6-line)",letterSpacing:"var(--h6-tracking)"}}>{title}</h2>}
    <div style={{padding:title?"0 24px 20px":"20px 24px",flex:"1 1 auto",overflowY:"auto"}}>{children}</div>
    {actions&&<div style={{display:"flex",alignItems:"center",justifyContent:"flex-end",padding:"8px 16px 16px",gap:8,flexWrap:"wrap"}}>{actions}</div>}
  </div>);
  if(inline)return paper;
  return <div onClick={onClose} style={{position:"fixed",inset:0,zIndex:1300,background:"var(--backdrop)",display:"flex",alignItems:"center",justifyContent:"center"}}>{paper}</div>;
}
