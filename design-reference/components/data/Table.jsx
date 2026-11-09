import React from "react";
/** Small dense MUI table (size="small"): History, conversion steps, pipeline. */
export function Table({columns=[],rows=[],ariaLabel,style}){
  const cell=(align,head)=>({padding:"6px 16px",borderBottom:"1px solid var(--table-border)",textAlign:align||"left",fontSize:"var(--body2-size)",lineHeight:head?"1.5rem":"var(--body2-line)",letterSpacing:"var(--body2-tracking)",fontWeight:head?"var(--table-head-weight)":400,color:head?"var(--table-head-color)":"var(--text-primary)",...(head?{fontSize:"var(--table-head-size)",textTransform:"var(--table-head-transform)",letterSpacing:"var(--table-head-tracking)"}:{}),fontVariantNumeric:"tabular-nums"});
  return(<table aria-label={ariaLabel} style={{width:"100%",borderCollapse:"collapse",borderSpacing:0,...style}}>
    <thead><tr>{columns.map(c=><th key={c.key} style={cell(c.align,true)}>{c.label}</th>)}</tr></thead>
    <tbody>{rows.map((r,i)=><tr key={i}>{columns.map(c=><td key={c.key} style={cell(c.align)}>{r[c.key]}</td>)}</tr>)}</tbody>
  </table>);
}
