// Small kit-local helpers (layout + visual anchors — all primitives come from the design system).
const H1=({children})=><h1 style={{margin:"0 0 16px",fontFamily:"var(--font-heading)",fontSize:"var(--h4-size)",fontWeight:"var(--h4-weight)",lineHeight:"var(--h4-line)",letterSpacing:"var(--h4-tracking)"}}>{children}</h1>;
const H2=({children,style})=><h2 style={{margin:"0 0 12px",fontFamily:"var(--font-heading)",fontSize:"var(--h5-size)",fontWeight:"var(--h5-weight)",lineHeight:"var(--h5-line)",letterSpacing:"var(--h5-tracking)",...style}}>{children}</h2>;
const Muted=({children,style})=><p style={{margin:"0 0 12px",color:"var(--text-secondary)",...style}}>{children}</p>;
const Count=({n,one,many})=><Muted style={{margin:"0 0 10px",fontSize:"var(--body2-size)",fontVariantNumeric:"tabular-nums"}}>{n===1?"1 "+one:n+" "+many}</Muted>;
const Stack=({gap=16,children,style})=><div style={{display:"grid",gap,paddingTop:8,...style}}>{children}</div>;
const Row=({children,style})=><div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap",...style}}>{children}</div>;
const Actions=({children})=><div style={{display:"flex",gap:4,alignItems:"center"}}>{children}</div>;
function ConfirmDialog({title,text,verb,onClose,onConfirm,danger}){const {Dialog,Button}=window.DS;
  return <Dialog title={title} onClose={onClose} actions={<><Button onClick={onClose}>Cancel</Button><Button variant="contained" color={danger?"error":"primary"} onClick={onConfirm}>{verb}</Button></>}><p style={{margin:0,color:"var(--text-secondary)"}}>{text}</p></Dialog>;}

/* ---------- Visual anchors ---------- */
// One icon family (Material Icons Outlined = @mui/icons-material *Outlined), muted by default.
const Icon=({name,size=18,style})=><span className="material-icons-outlined" aria-hidden="true" style={{fontSize:size,width:size,height:size,lineHeight:1,display:"inline-block",overflow:"hidden",flexShrink:0,...style}}>{name}</span>;
const Sep=()=><span aria-hidden="true" style={{color:"var(--text-disabled)"}}>·</span>;

const AVATAR_TONES=["blue","indigo","teal","amber","green","red","orange"];
const hashStr=s=>{let h=0;for(const c of String(s||""))h=(h*31+c.charCodeAt(0))|0;return Math.abs(h);};
const domainOf=name=>{const c=window.KIT_DATA.companies.find(c=>c.name===name);return c&&c.website;};
/** Company logo by domain (favicon service), falling back to an initial on a tone hashed from the name. */
function CompanyAvatar({name,domain,size=32}){
  const d=domain||domainOf(name);const real=d&&!/\.example$/.test(d);
  const[failed,setFailed]=React.useState(false);
  const t=AVATAR_TONES[hashStr(name)%AVATAR_TONES.length];
  const box={width:size,height:size,borderRadius:Math.round(size*0.3),flexShrink:0,display:"grid",placeItems:"center",overflow:"hidden",boxShadow:"inset 0 0 0 1px var(--divider)",boxSizing:"border-box"};
  if(real&&!failed)return <img src={"https://www.google.com/s2/favicons?domain="+encodeURIComponent(d)+"&sz=64"} alt="" width={size} height={size} onError={()=>setFailed(true)} style={{...box,background:"var(--bg-paper)",objectFit:"contain",padding:Math.round(size*0.14)}}/>;
  return <span aria-hidden="true" style={{...box,background:"var(--tone-"+t+"-bg)",color:"var(--tone-"+t+"-fg)",fontFamily:"var(--font-family)",fontWeight:600,fontSize:Math.round(size*0.42),lineHeight:1}}>{(name||"?").trim().charAt(0).toUpperCase()}</span>;
}
/** Square icon tile for things that aren't companies (profiles, job boards). */
const IconTile=({name,size=32,tone="neutral"})=><span aria-hidden="true" style={{width:size,height:size,borderRadius:Math.round(size*0.3),flexShrink:0,display:"grid",placeItems:"center",background:"var(--tone-"+tone+"-bg)",color:"var(--tone-"+tone+"-fg)"}}><Icon name={name} size={Math.round(size*0.56)}/></span>;

/** Two-line cell: lead visual + primary line (medium) + muted metadata line. */
function TwoLine({lead,primary,secondary}){
  const ell={overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"};
  return <div style={{display:"flex",alignItems:"center",gap:12,minWidth:0,width:"100%"}}>{lead}
    <div style={{minWidth:0,display:"grid",gap:2}}>
      <div style={{...ell,fontWeight:500}}>{primary}</div>
      {secondary&&<div style={{...ell,display:"flex",alignItems:"center",gap:6,fontSize:"var(--caption-size)",lineHeight:1.4,color:"var(--text-secondary)"}}>{secondary}</div>}
    </div></div>;
}
const Meta=({icon,children,mono})=><span style={{display:"inline-flex",alignItems:"center",gap:4,minWidth:0,fontFamily:mono?"var(--font-mono)":undefined}}>{icon&&<Icon name={icon} size={14}/>}{children}</span>;

const FEEDS=["remoteok","remotive","himalayas","jobicy"];
const sourceIcon=s=>!s?"edit_note":FEEDS.includes(s)?"rss_feed":"travel_explore";
const CHANNEL_ICONS={portal:"language",referral:"handshake",recruiter_inbound:"call_received",direct:"send",networking:"hub"};

// The kit's "today" is Mar 5, 2026 (same as the sample data).
const TODAY=new Date("Mar 5, 2026");
function RelDate({value}){
  if(!value)return <span style={{color:"var(--text-disabled)"}}>—</span>;
  const d=Math.round((TODAY-new Date(value))/864e5);
  const txt=d<=0?"today":d===1?"yesterday":d<7?d+"d ago":d<35?Math.round(d/7)+"w ago":value;
  return <time dateTime={new Date(value).toISOString().slice(0,10)} title={value} style={{color:"var(--text-secondary)",fontVariantNumeric:"tabular-nums"}}>{txt}</time>;
}

/** Priority as 3 ascending bars + the raw value. */
function PriorityBars({value,showLabel=true}){
  if(!value)return <span style={{color:"var(--text-disabled)"}}>—</span>;
  const n={high:3,medium:2,low:1}[value]||0;const c={high:"var(--tone-red-fg)",medium:"var(--tone-amber-fg)",low:"var(--text-secondary)"}[value];
  return <span style={{display:"inline-flex",alignItems:"center",gap:8}}>
    <span role="img" aria-label={"Priority "+value} style={{display:"inline-flex",alignItems:"flex-end",gap:2,height:12}}>{[6,9,12].map((h,i)=><span key={i} style={{width:3,height:h,borderRadius:1,background:i<n?c:"var(--divider)"}}/>)}</span>
    {showLabel&&<span style={{color:"var(--text-secondary)",fontSize:"var(--caption-size)"}}>{value}</span>}
  </span>;
}

/** Segmented bar: how far along the funnel. Greyed when the application is closed. */
function StageProgress({stage,outcome,segment=14,height=4}){
  const S=window.KIT_DATA.stages;const i=S.indexOf(stage);
  const fill=outcome?"var(--text-disabled)":"var(--primary-main)";
  return <span role="img" aria-label={"Stage "+(i+1)+" of "+S.length+(outcome?", closed":"")} title={stage+(outcome?" · "+outcome:"")} style={{display:"inline-flex",gap:3}}>
    {S.map((s,k)=><span key={s} style={{width:segment,height,borderRadius:height,background:k<=i?fill:"var(--divider)"}}/>)}
  </span>;
}

/** Vertical history: newest first, a dot with the stage icon, a hairline joining them. */
function Timeline({transitions}){
  const {StageChip}=window.DS;const items=[...transitions].reverse();
  return <ol style={{listStyle:"none",margin:0,padding:0}}>
    {items.map((t,i)=>{const last=i===items.length-1;return <li key={i} style={{display:"grid",gridTemplateColumns:"28px 1fr",columnGap:14}}>
      <div style={{display:"flex",flexDirection:"column",alignItems:"center"}}>
        <span aria-hidden="true" style={{width:28,height:28,borderRadius:"50%",display:"grid",placeItems:"center",background:i===0?"var(--primary-a12)":"var(--tone-neutral-bg)",color:i===0?"var(--primary-main)":"var(--text-secondary)"}}><Icon name={(window.DS.StageChip.ICONS||{})[t.outcome||t.to_stage]||"circle"} size={15}/></span>
        {!last&&<span style={{flex:1,width:1,minHeight:16,background:"var(--divider)",margin:"4px 0"}}/>}
      </div>
      <div style={{paddingBottom:last?0:20,minWidth:0}}>
        <div style={{display:"flex",alignItems:"center",gap:8,flexWrap:"wrap",minHeight:28}}>
          <StageChip value={t.to_stage} icon={false}/>{t.outcome&&<StageChip value={t.outcome} icon={false}/>}
          <span style={{marginLeft:"auto",fontFamily:"var(--font-mono)",fontSize:"var(--caption-size)",color:"var(--text-secondary)"}}>{t.date}</span>
        </div>
        {t.note&&<p style={{margin:"6px 0 0",color:"var(--text-secondary)",fontSize:"var(--body2-size)"}}>{t.note}</p>}
      </div>
    </li>;})}
  </ol>;
}

/** Empty grid/list: a large muted icon, a statement, an optional hint. */
const EmptyState=({icon,title,text})=><div style={{display:"grid",justifyItems:"center",gap:6,textAlign:"center",padding:"16px 0"}}>
  <span aria-hidden="true" style={{width:48,height:48,borderRadius:14,display:"grid",placeItems:"center",background:"var(--tone-neutral-bg)",color:"var(--text-secondary)",marginBottom:6}}><Icon name={icon} size={24}/></span>
  <span style={{color:"var(--text-primary)",fontWeight:500}}>{title}</span>
  {text&&<span style={{color:"var(--text-secondary)",fontSize:"var(--body2-size)",maxWidth:320,whiteSpace:"normal"}}>{text}</span>}
</div>;

/** Small figure tile for Metrics. */
function StatTile({icon,label,value,hint,tone="neutral"}){const {Paper}=window.DS;
  return <Paper padding={16} style={{display:"grid",gap:10,minWidth:0}}>
    <div style={{display:"flex",alignItems:"center",gap:8,color:"var(--text-secondary)",fontSize:"var(--body2-size)"}}><IconTile name={icon} size={28} tone={tone}/>{label}</div>
    <div style={{fontFamily:"var(--font-mono)",fontSize:"1.75rem",fontWeight:500,lineHeight:1.1,fontVariantNumeric:"tabular-nums"}}>{value}</div>
    {hint&&<div style={{color:"var(--text-secondary)",fontSize:"var(--caption-size)"}}>{hint}</div>}
  </Paper>;
}

/** Keyword token: neutral, or red with a minus for excluded ones. */
const Token=({children,excluded})=><span style={{display:"inline-flex",alignItems:"center",height:20,padding:"0 6px",borderRadius:6,background:excluded?"var(--tone-red-bg)":"var(--tone-neutral-bg)",color:excluded?"var(--tone-red-fg)":"var(--tone-neutral-fg)",fontFamily:"var(--font-mono)",fontSize:11.5,whiteSpace:"nowrap"}}>{excluded?"−":""}{children}</span>;
const Tokens=({items,excluded})=>items.length?<span style={{display:"inline-flex",gap:4,overflow:"hidden"}}>{items.map(x=><Token key={x} excluded={excluded}>{x}</Token>)}</span>:<span style={{color:"var(--text-disabled)"}}>—</span>;

/** Tab label with a muted count pill. */
const TabLabel=({label,n})=><span style={{display:"inline-flex",alignItems:"center",gap:8}}>{label}<span style={{minWidth:20,height:20,padding:"0 6px",borderRadius:999,background:"var(--tone-neutral-bg)",color:"var(--tone-neutral-fg)",fontSize:11.5,fontVariantNumeric:"tabular-nums",display:"inline-grid",placeItems:"center",boxSizing:"border-box"}}>{n}</span></span>;

Object.assign(window,{H1,H2,Muted,Count,Stack,Row,Actions,ConfirmDialog,Icon,Sep,CompanyAvatar,IconTile,TwoLine,Meta,sourceIcon,CHANNEL_ICONS,RelDate,PriorityBars,StageProgress,Timeline,EmptyState,StatTile,Token,Tokens,TabLabel});
