function InboxScreen({offers,setOffers,notify}){
  const {PageHeader,Button,IconButton,Tabs,DataGrid,Link}=window.DS;
  const[status,setStatus]=React.useState("pending");const[dialog,setDialog]=React.useState(null);
  const rows=offers.filter(o=>o.status===status);
  const n=s=>offers.filter(o=>o.status===s).length;
  const set=(id,patch)=>setOffers(os=>os.map(o=>o.id===id?{...o,...patch}:o));
  const cols=[{field:"title",headerName:"Offer",flex:3,render:r=><TwoLine lead={<CompanyAvatar name={r.company}/>} primary={<Link href={r.url} external style={{fontWeight:500}}>{r.title}</Link>} secondary={<><span>{r.company||"—"}</span><Sep/><Meta icon={sourceIcon(r.source)}>{r.source||"manual"}</Meta></>}/>},
    ...(status==="discarded"?[{field:"discard_reason",headerName:"Reason",hideOnMobile:true,render:r=>r.discard_reason||<span style={{color:"var(--text-disabled)"}}>—</span>}]:[]),
    {field:"created_at",headerName:"Added",width:120,hideOnMobile:true,render:r=><RelDate value={r.created_at}/>},
    {field:"actions",headerName:"",width:150,mobileWidth:120,render:r=>r.status==="pending"?<Actions><Button size="small" onClick={()=>setDialog({type:"promote",offer:r})}>Promote</Button><span className="row-actions"><IconButton size="small" icon="close" label={"Discard “"+r.title+"”"} onClick={()=>setDialog({type:"discard",offer:r})}/></span></Actions>:r.status==="discarded"?<Button size="small" onClick={()=>{set(r.id,{status:"pending"});notify("Offer restored");}}>Restore</Button>:null}];
  const empty={pending:{icon:"inbox",title:"No offers",text:"Import a feed or add an offer to fill the inbox."},discarded:{icon:"delete_outline",title:"No offers",text:"Discarded offers are kept here so you can restore them."},promoted:{icon:"arrow_upward",title:"No offers",text:"Promoted offers become applications."}}[status];
  const close=()=>setDialog(null);
  return(<>
    <PageHeader title="Inbox" actions={<><Button variant="outlined" onClick={()=>setDialog({type:"import"})}>Import feed</Button><Button variant="contained" onClick={()=>setDialog({type:"add"})}>Add offer</Button></>}/>
    <Tabs value={status} onChange={setStatus} style={{marginBottom:20}} tabs={[{value:"pending",label:<TabLabel label="Pending" n={n("pending")}/>},{value:"discarded",label:<TabLabel label="Discarded" n={n("discarded")}/>},{value:"promoted",label:<TabLabel label="Promoted" n={n("promoted")}/>}]}/>
    <DataGrid columns={cols} rows={rows} rowHeight={64} noRowsLabel={<EmptyState {...empty}/>}/>
    {dialog&&dialog.type==="discard"&&<DiscardDialog offer={dialog.offer} onClose={close} onDone={(reason)=>{const id=dialog.offer.id;set(id,{status:"discarded",discard_reason:reason});close();notify("Offer discarded",()=>set(id,{status:"pending"}));}}/>}
    {dialog&&dialog.type==="promote"&&<PromoteDialog offer={dialog.offer} onClose={close} onDone={()=>{set(dialog.offer.id,{status:"promoted"});close();notify("Application created");}}/>}
    {dialog&&dialog.type==="add"&&<AddOfferDialog onClose={close} onAdd={(o)=>{setOffers(os=>[o,...os]);close();setStatus("pending");}}/>}
    {dialog&&dialog.type==="import"&&<ImportFeedDialog onClose={close}/>}
  </>);
}
function DiscardDialog({offer,onClose,onDone}){const {Dialog,Button,TextField}=window.DS;const[r,setR]=React.useState("");
  return <Dialog title={"Discard “"+offer.title+"”"} onClose={onClose} actions={<><Button onClick={onClose}>Cancel</Button><Button variant="contained" onClick={()=>onDone(r)}>Discard</Button></>}><Stack><TextField label="Reason" placeholder="Optional" fullWidth autoFocus value={r} onChange={setR}/></Stack></Dialog>;}
function PromoteDialog({offer,onClose,onDone}){const {Dialog,Button,TextField}=window.DS;
  return <Dialog title={"Promote “"+offer.title+"”"} onClose={onClose} actions={<><Button onClick={onClose}>Cancel</Button><Button variant="contained" onClick={onDone}>Promote</Button></>}>
    <Stack><div style={{display:"flex",alignItems:"center",gap:12}}><CompanyAvatar name={offer.company} size={36}/><p style={{margin:0,color:"var(--text-secondary)"}}>Creates an application in stage evaluated for {offer.company}.</p></div><TextField label="Channel" select fullWidth defaultValue="portal" options={window.KIT_DATA.channels}/></Stack></Dialog>;}
function AddOfferDialog({onClose,onAdd}){const {Dialog,Button,TextField}=window.DS;const[t,setT]=React.useState("");const[c,setC]=React.useState("");const[err,setErr]=React.useState(false);
  const add=()=>{if(!t){setErr(true);return;}onAdd({id:"o"+Date.now(),title:t,company:c,source:"",created_at:"Mar 5, 2026",status:"pending",url:"#"});};
  return <Dialog title="Add offer" onClose={onClose} actions={<><Button onClick={onClose}>Cancel</Button><Button variant="contained" onClick={add}>Add</Button></>}>
    <Stack><TextField label="URL" fullWidth autoFocus/><TextField label="Company" fullWidth value={c} onChange={setC}/><TextField label="Title" fullWidth value={t} onChange={x=>{setT(x);setErr(false);}} error={err} helperText={err?"Field required":undefined}/>
    <TextField label="Job board" select fullWidth shrink defaultValue="" options={[{value:"",label:"None"},...window.KIT_DATA.jobBoards.map(j=>({value:j.id,label:j.name}))]}/><TextField label="Notes" multiline minRows={2} fullWidth/></Stack></Dialog>;}
function ImportFeedDialog({onClose}){const {Dialog,Button,TextField,Alert}=window.DS;const D=window.KIT_DATA;
  const[feed,setFeed]=React.useState("");const[p,setP]=React.useState("");const[res,setRes]=React.useState(null);const[loading,setLoading]=React.useState(false);
  const go=()=>{if(!feed||!p){setRes({err:!feed?"feed":"profile"});return;}setLoading(true);setTimeout(()=>{setLoading(false);setRes(feed==="remoteok"?{cool:true}:{ok:true});},700);};
  return <Dialog title="Import feed" onClose={onClose} actions={<><Button onClick={onClose}>Close</Button><Button variant="contained" loading={loading} onClick={go}>Import</Button></>}>
    <Stack>
      {res&&res.cool&&<Alert severity="warning">remoteok can be imported again in 5 hours</Alert>}
      {res&&res.ok&&<Alert severity="success">48 found, 9 matching, 6 added, 3 already in the inbox, 0 expired</Alert>}
      <TextField label="Feed" select fullWidth value={feed} onChange={setFeed} options={D.feeds} error={res&&res.err==="feed"} helperText={res&&res.err==="feed"?"Choose a feed":undefined}/>
      <TextField label="Search profile" select fullWidth value={p} onChange={setP} options={D.profiles.map(x=>({value:x.id,label:x.name}))} error={res&&res.err==="profile"} helperText={res&&res.err==="profile"?"Choose a search profile":undefined}/>
    </Stack></Dialog>;}
window.InboxScreen=InboxScreen;
