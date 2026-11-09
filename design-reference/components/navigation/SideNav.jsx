import React from "react";
/** 240px drawer: product name in a 64px toolbar, then a flat list of screens (optional leading icon per item). "temporary" = mobile overlay. */
export function SideNav({title="Job Offer Funnel",items=[],active,onNavigate,footer,variant="permanent",open=false,onClose,style}){
  const panel=(<nav aria-label="Main" style={{width:"var(--drawer-width)",flexShrink:0,background:"var(--surface-nav)",borderRight:"1px solid var(--divider)",height:"100%",minHeight:variant==="permanent"?"100vh":undefined,display:"flex",flexDirection:"column",boxSizing:"border-box",...(variant==="permanent"?style:{})}}>
    <div style={{minHeight:"var(--toolbar-height)",display:"flex",alignItems:"center",padding:"0 24px",fontFamily:"var(--wordmark-font)",fontSize:"var(--h6-size)",fontWeight:"var(--wordmark-weight)",lineHeight:"var(--h6-line)",letterSpacing:"var(--h6-tracking)",color:"var(--text-primary)"}}>{title}</div>
    <div style={{padding:"8px 0",flex:1}}>{items.map(it=><Item key={it.path} icon={it.icon} active={it.path===active} onClick={()=>{onNavigate&&onNavigate(it.path);onClose&&onClose();}}>{it.label}</Item>)}</div>
    {footer&&<div style={{padding:"12px 16px",borderTop:"1px solid var(--divider)"}}>{footer}</div>}
  </nav>);
  if(variant==="permanent")return panel;
  return(<div style={{position:"fixed",inset:0,zIndex:1200,pointerEvents:open?"auto":"none"}}>
    <div onClick={onClose} style={{position:"absolute",inset:0,background:"var(--backdrop)",opacity:open?1:0,transition:"opacity 225ms var(--ease-standard)"}}/>
    <div style={{position:"absolute",top:0,bottom:0,left:0,transform:open?"none":"translateX(-100%)",transition:"transform 225ms var(--ease-standard)",boxShadow:open?"var(--shadow-dialog)":"none",...style}}>{panel}</div>
  </div>);
}
function Item({active,onClick,icon,children}){const[h,setH]=React.useState(false);
  return <div role="link" aria-current={active?"page":undefined} onClick={onClick} onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)} style={{padding:"8px 16px",margin:"1px var(--nav-item-inset)",borderRadius:"var(--nav-item-radius)",cursor:"pointer",background:active?"var(--nav-active-bg)":h?"var(--action-hover)":"transparent",color:active?"var(--nav-active-fg)":"var(--text-primary)",fontWeight:active?"var(--button-weight)":400,fontSize:"var(--nav-font-size)",lineHeight:1.5}}><span style={{display:"flex",alignItems:"center",gap:12,margin:"2px 0"}}>{icon&&<span className="material-icons-outlined" aria-hidden="true" style={{fontSize:20,width:20,overflow:"hidden",color:active?"var(--nav-active-fg)":"var(--text-secondary)"}}>{icon}</span>}{children}</span></div>;}
