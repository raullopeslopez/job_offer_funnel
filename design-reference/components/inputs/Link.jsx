import React from "react";
/** Primary-colored link with a 40% underline that solidifies on hover. */
export function Link({href="#",external=false,onClick,children,style}){
  const[h,setH]=React.useState(false);
  return <a href={href} onClick={onClick} target={external?"_blank":undefined} rel={external?"noopener noreferrer":undefined} onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)} style={{color:"var(--primary-main)",textDecoration:h?"underline":"var(--link-underline)",textDecorationColor:h?"inherit":"var(--primary-a40)",textUnderlineOffset:"0.15em",cursor:"pointer",...style}}>{children}</a>;
}
