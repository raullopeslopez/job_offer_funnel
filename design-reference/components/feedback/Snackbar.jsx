import React from "react";
/** Dark toast, bottom-left, with optional action (Undo). Set inline to render in flow (docs/cards). */
export function Snackbar({open=true,message,action,inline=false,style}){
  if(!open)return null;
  const pos=inline?{}:{position:"fixed",left:16,bottom:16,width:"max-content",maxWidth:"calc(100% - 32px)",zIndex:1400};
  return(<div style={{...pos,display:"flex",alignItems:"center",flexWrap:"wrap",minWidth:288,padding:"6px 16px",borderRadius:"var(--radius)",background:"var(--snackbar-bg)",color:"var(--snackbar-fg)",boxShadow:"var(--shadow-snackbar)",fontSize:"var(--body2-size)",lineHeight:"var(--body2-line)",letterSpacing:"var(--body2-tracking)",boxSizing:"border-box",...style}}>
    <div style={{padding:"8px 0",flex:1}}>{message}</div>
    {action&&<div style={{display:"flex",alignItems:"center",marginLeft:"auto",paddingLeft:16,marginRight:-8}}>{action}</div>}
  </div>);
}
