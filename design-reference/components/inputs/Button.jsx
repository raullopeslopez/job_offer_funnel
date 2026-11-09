import React from "react";
function useHover(){const[h,setH]=React.useState(false);return[h,{onMouseEnter:()=>setH(true),onMouseLeave:()=>setH(false)}];}
let spinInjected=false;
function injectSpin(){if(spinInjected||typeof document==="undefined")return;spinInjected=true;const s=document.createElement("style");s.textContent="@keyframes jof-spin{to{transform:rotate(360deg)}}";document.head.appendChild(s);}
const PAD={contained:{medium:"6px 16px",small:"4px 10px"},outlined:{medium:"5px 15px",small:"3px 9px"},text:{medium:"6px 8px",small:"4px 5px"}};
const COLORS={primary:{main:"var(--primary-main)",dark:"var(--primary-dark)",a04:"var(--primary-a04)",a50:"var(--primary-a50)",contrast:"var(--primary-contrast)"},secondary:{main:"var(--secondary-main)",dark:"var(--secondary-dark)",a04:"rgba(0,137,123,0.04)",a50:"rgba(0,137,123,0.5)",contrast:"#fff"},error:{main:"var(--error-main)",dark:"var(--error-dark)",a04:"var(--error-a04)",a50:"var(--error-a50)",contrast:"#fff"},inherit:{main:"inherit",dark:"inherit",a04:"var(--action-hover)",a50:"var(--input-border)",contrast:"inherit"}};
/** MUI-style button: uppercase 14/500 label, 8px radius. */
export function Button({variant="text",color="primary",size="medium",fullWidth=false,loading=false,disabled=false,type="button",onClick,children,style}){
  injectSpin();
  const[h,hp]=useHover();const c=COLORS[color]||COLORS.primary;const off=disabled||loading;
  const base={fontFamily:"var(--font-family)",fontWeight:"var(--button-weight)",fontSize:size==="small"?"var(--button-small-size)":"var(--button-size)",lineHeight:"var(--button-line)",letterSpacing:"var(--button-tracking)",textTransform:"var(--button-transform)",borderRadius:"var(--radius)",minWidth:64,padding:PAD[variant][size],border:0,cursor:off?"default":"pointer",display:"inline-flex",alignItems:"center",justifyContent:"center",position:"relative",width:fullWidth?"100%":undefined,transition:"background-color 250ms var(--ease-standard), box-shadow 250ms var(--ease-standard), border-color 250ms var(--ease-standard)",boxSizing:"border-box",whiteSpace:"nowrap"};
  let v;
  if(variant==="contained") v={background:off?"var(--action-disabled-bg)":(h?c.dark:c.main),color:off?"var(--text-disabled)":c.contrast,boxShadow:off?"none":(h?"var(--shadow-button-hover)":"var(--shadow-button)")};
  else if(variant==="outlined") v={background:h&&!off?c.a04:"transparent",color:off?"var(--text-disabled)":c.main,border:"1px solid "+(off?"var(--action-disabled-bg)":(h?c.main:c.a50))};
  else v={background:h&&!off?c.a04:"transparent",color:off?"var(--text-disabled)":c.main};
  return(<button type={type} disabled={off} onClick={onClick} {...hp} style={{...base,...v,...style}}>
    <span style={{visibility:loading?"hidden":"visible"}}>{children}</span>
    {loading&&<span aria-label="Loading" style={{position:"absolute",width:16,height:16,borderRadius:"50%",border:"2px solid var(--text-disabled)",borderTopColor:"transparent",animation:"jof-spin 1s linear infinite"}}/>}
  </button>);
}
