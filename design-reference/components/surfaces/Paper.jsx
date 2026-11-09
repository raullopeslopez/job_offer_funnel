import React from "react";
/** White surface, 8px radius, elevation 1 by default. */
export function Paper({elevation=1,padding=0,children,style,as="div",...rest}){
  const Tag=as;
  return <Tag {...rest} style={{"--label-bg":"var(--bg-paper)",background:"var(--bg-paper)",color:"var(--text-primary)",borderRadius:"var(--radius-lg)",boxShadow:"var(--elevation-"+elevation+")",padding,...style}}>{children}</Tag>;
}
