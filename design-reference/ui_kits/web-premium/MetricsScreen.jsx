function MetricsScreen({mobile}){
  const {Table,BarChart,Paper,StageChip}=window.DS;const D=window.KIT_DATA;
  const fmt=r=>r===null?"—":r.toFixed(1)+"%";
  const total=D.pipeline.reduce((a,s)=>a+s.n,0);
  const n=s=>(D.pipeline.find(p=>p.stage===s)||{n:0}).n;
  const resp=D.conversion.find(c=>c.from==="applied");
  const RateCell=({rate})=><span style={{display:"inline-flex",alignItems:"center",gap:10,justifyContent:"flex-end"}}>
    {!mobile&&<span aria-hidden="true" style={{width:64,height:4,borderRadius:4,background:"var(--divider)",overflow:"hidden"}}><span style={{display:"block",height:"100%",width:(rate||0)+"%",background:"var(--chart-series-1)",borderRadius:4}}/></span>}
    <span style={{fontFamily:"var(--font-mono)",fontWeight:500,minWidth:52,textAlign:"right"}}>{fmt(rate)}</span></span>;
  return(<>
    <H1>Metrics</H1>
    <div style={{display:"grid",gridTemplateColumns:mobile?"1fr 1fr":"repeat(4, minmax(0,1fr))",gap:mobile?12:16,marginBottom:32}}>
      <StatTile icon="work" label="Active" value={total} hint="applications in the pipeline" tone="indigo"/>
      <StatTile icon="groups" label="Interviewing" value={n("interviewing")} hint="applications" tone="amber"/>
      <StatTile icon="mark_email_read" label="Response rate" value={fmt(resp&&resp.rate)} hint="applied → screening" tone="teal"/>
      <StatTile icon="workspace_premium" label="Offers" value={n("offer")} hint="applications" tone="green"/>
    </div>
    <div style={{display:"grid",gap:32,gridTemplateColumns:"minmax(0,1fr)"}}>
      <section style={{minWidth:0}}><H2>Conversion by stage</H2>
        <Paper padding={0} style={{overflow:"hidden"}}>
          <div style={{overflowX:"auto"}}><Table ariaLabel="Conversion by stage" columns={[{key:"f",label:"From"},{key:"t",label:"To"},{key:"rf",label:"Reached from",align:"right"},{key:"rt",label:"Reached to",align:"right"},{key:"r",label:"Rate",align:"right"}]} rows={D.conversion.map(s=>({...s,f:<StageChip value={s.from}/>,t:<StageChip value={s.to}/>,r:<RateCell rate={s.rate}/>}))}/></div>
          <div style={{padding:"8px 16px 16px"}}><BarChart seriesLabel="Rate" max={100} labels={D.conversion.map(s=>mobile?s.to:s.from+" → "+s.to)} values={D.conversion.map(s=>s.rate)} format={fmt}/></div>
        </Paper>
      </section>
      <section style={{minWidth:0}}><H2>Active pipeline</H2>
        <Muted><span style={{fontFamily:"var(--font-mono)",color:"var(--text-primary)",fontWeight:500}}>{total}</span> active applications in total</Muted>
        <Paper padding={0} style={{overflow:"hidden"}}>
          <Table ariaLabel="Active pipeline" columns={[{key:"s",label:"Stage"},{key:"n",label:"Applications",align:"right"}]} rows={D.pipeline.map(p=>({s:<StageChip value={p.stage}/>,n:<span style={{fontFamily:"var(--font-mono)"}}>{p.n}</span>}))}/>
          <div style={{padding:"8px 16px 16px"}}><BarChart seriesLabel="Active" labels={D.pipeline.map(s=>s.stage)} values={D.pipeline.map(s=>s.n)}/></div>
        </Paper>
      </section>
    </div>
  </>);
}
window.MetricsScreen=MetricsScreen;
