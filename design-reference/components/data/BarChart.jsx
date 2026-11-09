import React from "react";
/** Simplified MUI X BarChart: single series, y axis with ticks, x labels, legend on top. */
export function BarChart({labels=[],values=[],seriesLabel,max,height=240,format=v=>v,style}){
  const top=max??Math.max(1,...values.map(v=>v||0));
  const ticks=[0,0.25,0.5,0.75,1].map(t=>Math.round(top*t*10)/10);
  const plotH=height-80;
  return(<div style={{height,display:"flex",flexDirection:"column",fontSize:12,color:"var(--text-secondary)",fontFamily:"var(--font-family)",...style}}>
    {seriesLabel&&<div style={{display:"flex",justifyContent:"center",alignItems:"center",gap:8,height:28,fontSize:13,color:"var(--text-primary)"}}><span style={{width:14,height:14,borderRadius:2,background:"var(--chart-series-1)"}}/>{seriesLabel}</div>}
    <div style={{display:"flex",flex:1,padding:"8px 20px 0 0"}}>
      <div style={{width:44,position:"relative",height:plotH,borderRight:"1px solid var(--divider)"}}>
        {ticks.map(t=><div key={t} style={{position:"absolute",right:6,bottom:(t/top)*plotH-7,fontSize:12,fontFamily:"var(--font-mono)"}}>{t}</div>)}
      </div>
      <div style={{flex:1,display:"flex",flexDirection:"column"}}>
        <div style={{height:plotH,display:"flex",alignItems:"flex-end",borderBottom:"1px solid var(--divider)"}}>
          {values.map((v,i)=><div key={i} title={format(v)} style={{flex:1,display:"flex",justifyContent:"center",alignItems:"flex-end",height:"100%"}}><div style={{width:"64%",height:((v||0)/top*100)+"%",background:"var(--chart-series-1)",borderRadius:"calc(var(--radius) - 6px) calc(var(--radius) - 6px) 0 0",maxWidth:56}}/></div>)}
        </div>
        <div style={{display:"flex"}}>{labels.map((l,i)=><div key={i} style={{flex:1,textAlign:"center",paddingTop:6,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{l}</div>)}</div>
      </div>
    </div>
  </div>);
}
