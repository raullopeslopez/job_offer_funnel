import React from "react";
/** Outlined MUI-style text field; also covers select (options) and multiline. */
export function TextField({label,value,defaultValue,onChange,placeholder,helperText,error=false,size="medium",select=false,options=[],multiline=false,minRows=2,type="text",fullWidth=false,shrink,autoFocus,disabled,style}){
  const[inner,setInner]=React.useState(defaultValue??"");
  const val=value!==undefined?value:inner;
  const set=(v)=>{if(value===undefined)setInner(v);onChange&&onChange(v);};
  const[focus,setFocus]=React.useState(false);const[open,setOpen]=React.useState(false);const[hover,setHover]=React.useState(false);
  const small=size==="small";
  const hasVal=Array.isArray(val)?val.length>0:val!==""&&val!=null;
  const floated=shrink||focus||open||hasVal||!!placeholder||type==="date";
  const accent=error?"var(--error-main)":"var(--primary-main)";
  const borderColor=error?"var(--error-main)":(focus||open)?"var(--primary-main)":hover?"var(--text-primary)":"var(--input-border)";
  const bw=(focus||open)?2:1;
  const pad=small?"8.5px 14px":"16.5px 14px";
  const font={fontFamily:"var(--font-family)",fontSize:"var(--body1-size)",lineHeight:"1.4375em",letterSpacing:"var(--body1-tracking)",color:"var(--text-primary)"};
  const labelStyle={position:"absolute",left:0,top:0,transformOrigin:"top left",pointerEvents:"none",whiteSpace:"nowrap",...font,color:error?"var(--error-main)":(focus||open)?"var(--primary-main)":"var(--text-secondary)",transition:"transform 200ms var(--ease-standard), color 200ms",transform:floated?"translate(14px,-9px) scale(0.75)":(small?"translate(14px,9px) scale(1)":"translate(14px,16px) scale(1)"),background:floated?"linear-gradient(to bottom, var(--label-bg, var(--bg-paper)) 50%, var(--input-bg) 50%)":"transparent",padding:floated?"0 5px":0,marginLeft:floated?-5:0};
  const opt=options.map(o=>typeof o==="string"?{value:o,label:o}:o);
  const shown=select?(Array.isArray(val)?opt.filter(o=>val.includes(o.value)).map(o=>o.label).join(", "):(opt.find(o=>o.value===val)?.label??"")):null;
  const inputBase={...font,border:0,outline:0,background:"transparent",padding:pad,width:"100%",boxSizing:"border-box",display:"block",resize:"none",minHeight:select?"1.4375em":undefined};
  return(<div style={{display:"inline-flex",flexDirection:"column",position:"relative",minWidth:0,width:fullWidth?"100%":undefined,verticalAlign:"top",...style}}>
    <div onMouseEnter={()=>setHover(true)} onMouseLeave={()=>setHover(false)} style={{position:"relative",borderRadius:"var(--radius)",background:"var(--input-bg)",cursor:select?"pointer":"text"}} onClick={select&&!disabled?()=>setOpen(!open):undefined}>
      {select?<div tabIndex={0} onFocus={()=>setFocus(true)} onBlur={()=>setFocus(false)} style={{...inputBase,paddingRight:32,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",userSelect:"none"}}>{shown||placeholder||"​"}</div>
      :multiline?<textarea autoFocus={autoFocus} rows={minRows} value={val} placeholder={placeholder} onChange={e=>set(e.target.value)} onFocus={()=>setFocus(true)} onBlur={()=>setFocus(false)} style={{...inputBase,padding:0,margin:pad}} />
      :<input autoFocus={autoFocus} disabled={disabled} type={type} value={val} placeholder={placeholder} onChange={e=>set(e.target.value)} onFocus={()=>setFocus(true)} onBlur={()=>setFocus(false)} style={inputBase}/>}
      {select&&<span className="material-icons-outlined" style={{position:"absolute",right:7,top:"calc(50% - 12px)",fontSize:24,color:"var(--action-active)",transform:open?"rotate(180deg)":"none",pointerEvents:"none"}}>arrow_drop_down</span>}
      <div style={{position:"absolute",inset:0,border:bw+"px solid "+borderColor,borderRadius:"var(--radius)",pointerEvents:"none"}}/>
      {label&&<label style={labelStyle}>{label}</label>}
      {select&&open&&<div onClick={e=>e.stopPropagation()} style={{position:"absolute",left:0,top:"100%",marginTop:4,minWidth:"100%",background:"var(--bg-paper)",borderRadius:"var(--radius)",boxShadow:"var(--shadow-menu)",padding:"4px 0",zIndex:1300,maxHeight:300,overflow:"auto"}}>
        {opt.map(o=>{const sel=Array.isArray(val)?val.includes(o.value):val===o.value;return(<MenuItem key={o.value} selected={sel} onClick={()=>{if(Array.isArray(val)){set(sel?val.filter(x=>x!==o.value):[...val,o.value]);}else{set(o.value);setOpen(false);}}}>{o.label}</MenuItem>);})}
      </div>}
    </div>
    {helperText&&<p style={{margin:"3px 14px 0",fontSize:"var(--caption-size)",lineHeight:"var(--caption-line)",letterSpacing:"var(--caption-tracking)",color:error?"var(--error-main)":"var(--text-secondary)"}}>{helperText}</p>}
  </div>);
}
function MenuItem({selected,onClick,children}){const[h,setH]=React.useState(false);
  return <div onClick={onClick} onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)} style={{padding:"6px 12px",minHeight:"auto",fontSize:"var(--body1-size)",lineHeight:1.5,cursor:"pointer",whiteSpace:"nowrap",background:selected?(h?"var(--primary-a12)":"var(--primary-a08)"):h?"var(--action-hover)":"transparent",borderRadius:"calc(var(--radius) - 4px)",margin:"0 4px",fontFamily:"var(--font-family)",color:"var(--text-primary)"}}>{children||" "}</div>;}
