import React from "react";
const TONES={discovered:"neutral",evaluated:"blue",applied:"indigo",screening:"teal",interviewing:"amber",offer:"green",accepted:"green",
rejected:"red",ghosted:"neutral",withdrawn:"neutral",offer_declined:"orange",
high:"red",medium:"amber",low:"neutral",pending:"neutral",discarded:"neutral",promoted:"green",active:"indigo",closed:"neutral"};
/* Material Icons Outlined glyph per funnel value (same names as @mui/icons-material *Outlined). */
const ICONS={discovered:"explore",evaluated:"visibility",applied:"send",screening:"call",interviewing:"groups",offer:"workspace_premium",accepted:"verified",
rejected:"block",ghosted:"visibility_off",withdrawn:"undo",offer_declined:"do_not_disturb_on",pending:"schedule",discarded:"delete_outline",promoted:"arrow_upward"};
/** Tinted pill for funnel values (stage, outcome, priority, offer status). Shows the raw API value.
 *  Leads with the value's icon when it has one (icon={false} → dot); dot={false} → text only. */
export function StageChip({value,tone,dot=true,icon=true,size="small",style}){
  if(!value)return <span style={{color:"var(--text-disabled)"}}>—</span>;
  const t=tone||TONES[value]||"neutral";const glyph=dot&&icon&&ICONS[value];
  return(<span style={{display:"inline-flex",alignItems:"center",gap:glyph?4:6,height:size==="small"?22:26,padding:size==="small"?(glyph?"0 8px 0 6px":"0 8px"):(glyph?"0 10px 0 8px":"0 10px"),borderRadius:999,background:"var(--tone-"+t+"-bg)",color:"var(--tone-"+t+"-fg)",fontFamily:"var(--font-family)",fontSize:size==="small"?12:13,fontWeight:500,lineHeight:1,whiteSpace:"nowrap",letterSpacing:"0.01em",...style}}>
    {glyph?<span className="material-icons-outlined" aria-hidden="true" style={{fontSize:size==="small"?14:16,width:size==="small"?14:16,overflow:"hidden"}}>{glyph}</span>:dot&&<span style={{width:6,height:6,borderRadius:"50%",background:"currentColor",opacity:0.85}}/>}{value}
  </span>);
}
StageChip.ICONS=ICONS;
