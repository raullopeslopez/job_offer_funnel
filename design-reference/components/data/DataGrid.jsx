import React from "react";
/** Visual recreation of MUI X DataGrid as configured in the app: no sorting/menus, server pagination, autoHeight.
 *  Columns flagged hideOnMobile are hidden when the grid is narrower than 640px.
 *  rowHeight: taller rows for two-line cells. noRowsLabel may be a node (empty state). Rows carry class "ds-grid-row"
 *  so secondary actions wrapped in ".row-actions" can fade in on hover / focus. */
export function DataGrid({columns=[],rows=[],total,page=0,pageSize=20,onPageChange,noRowsLabel="No rows",hideFooter=false,rowHeight,style}){
  const ref=React.useRef(null);const[narrow,setNarrow]=React.useState(false);
  React.useEffect(()=>{if(!ref.current||typeof ResizeObserver==="undefined")return;const ro=new ResizeObserver(([e])=>setNarrow(e.contentRect.width<640));ro.observe(ref.current);return()=>ro.disconnect();},[]);
  const cols=narrow?columns.filter(c=>!c.hideOnMobile):columns;
  const count=total??rows.length;
  const from=count===0?0:page*pageSize+1, to=Math.min(count,(page+1)*pageSize);
  const w=c=>c.width?{width:narrow&&c.mobileWidth?c.mobileWidth:c.width,flex:"0 0 "+(narrow&&c.mobileWidth?c.mobileWidth:c.width)+"px"}:{flex:(c.flex||1)+" 1 0",minWidth:0};
  const cellBase={display:"flex",alignItems:"center",padding:"0 12px",boxSizing:"border-box",overflow:"hidden",whiteSpace:"nowrap",textOverflow:"ellipsis"};
  return(<div ref={ref} style={{border:"1px solid var(--table-border)",borderRadius:"var(--radius-lg)",background:"var(--bg-paper)",boxShadow:"var(--grid-shadow)",fontSize:"var(--body2-size)",lineHeight:"var(--body2-line)",letterSpacing:"var(--body2-tracking)",color:"var(--text-primary)",overflow:"hidden",...style}}>
    <div role="row" style={{display:"flex",height:"var(--grid-header-height)",borderBottom:"1px solid var(--table-border)",background:"var(--grid-header-bg)"}}>
      {cols.map((c,i)=><div key={c.field} role="columnheader" style={{...cellBase,...w(c),fontWeight:"var(--table-head-weight)",fontSize:"var(--table-head-size)",color:"var(--table-head-color)",textTransform:"var(--table-head-transform)",letterSpacing:"var(--table-head-tracking)",position:"relative"}}>{c.headerName}{i<cols.length-1&&<span style={{position:"absolute",right:0,top:"50%",height:14,marginTop:-7,width:1,background:"var(--grid-separator)"}}/>}</div>)}
    </div>
    {rows.length===0?<div style={{minHeight:104,padding:"24px 16px",boxSizing:"border-box",display:"grid",placeItems:"center",color:"var(--text-secondary)"}}>{noRowsLabel}</div>:
    rows.map((r,ri)=><Row key={r.id??ri} last={ri===rows.length-1} height={rowHeight}>{cols.map(c=><div key={c.field} role="cell" style={{...cellBase,...w(c)}}>{c.render?c.render(r):r[c.field]}</div>)}</Row>)}
    {!hideFooter&&<div style={{display:"flex",alignItems:"center",justifyContent:"flex-end",minHeight:52,borderTop:"1px solid var(--table-border)",padding:"0 8px 0 16px",gap:20,color:"var(--text-secondary)",fontVariantNumeric:"tabular-nums"}}>
      <span>{from}–{to} of {count}</span>
      <div style={{display:"flex",gap:4}}>
        <Icon disabled={page===0} onClick={()=>onPageChange&&onPageChange(page-1)} name="chevron_left" label="Go to previous page"/>
        <Icon disabled={to>=count} onClick={()=>onPageChange&&onPageChange(page+1)} name="chevron_right" label="Go to next page"/>
      </div>
    </div>}
  </div>);
}
function Row({children,last,height}){const[h,setH]=React.useState(false);return <div role="row" className="ds-grid-row" onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)} style={{display:"flex",height:height||"var(--grid-row-height)",borderBottom:last?0:"1px solid var(--table-border)",background:h?"var(--action-hover)":"transparent",transition:"background-color 120ms var(--ease-standard)"}}>{children}</div>;}
function Icon({name,disabled,onClick,label}){const[h,setH]=React.useState(false);return <button aria-label={label} disabled={disabled} onClick={onClick} onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)} style={{width:40,height:40,borderRadius:"var(--icon-button-radius)",border:0,display:"grid",placeItems:"center",cursor:disabled?"default":"pointer",background:h&&!disabled?"var(--action-hover)":"transparent",color:disabled?"var(--text-disabled)":"var(--action-active)"}}><span className="material-icons-outlined" style={{fontSize:24}}>{name}</span></button>;}
