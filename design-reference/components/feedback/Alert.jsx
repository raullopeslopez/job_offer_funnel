import React from "react";
const MAP={error:["error_outline","var(--error-main)"],info:["info","var(--info-main)"],success:["check_circle","var(--success-main)"],warning:["report_problem","var(--warning-main)"]};
/** Standard (tinted) MUI alert with outlined icon. */
export function Alert({severity="info",children,style}){
  const[icon,ic]=MAP[severity]||MAP.info;
  return(<div role="alert" style={{display:"flex",padding:"6px 16px",borderRadius:"var(--radius)",background:"var(--alert-"+severity+"-bg)",color:"var(--alert-"+severity+"-fg)",fontSize:"var(--body2-size)",lineHeight:"var(--body2-line)",letterSpacing:"var(--body2-tracking)",...style}}>
    <span className="material-icons-outlined" style={{marginRight:12,padding:"7px 0",fontSize:22,color:ic,opacity:0.9}}>{icon}</span>
    <div style={{padding:"8px 0",minWidth:0,overflow:"auto"}}>{children}</div>
  </div>);
}
