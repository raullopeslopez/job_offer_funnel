function ApplicationsScreen({applications,setApplications,onOpen,mobile}){
  const {PageHeader,Button,TextField,DataGrid,Link,StageChip}=window.DS;const D=window.KIT_DATA;
  const[f,setF]=React.useState({stage:"",outcome:"",channel:"",status:""});const[creating,setCreating]=React.useState(false);
  const rows=applications.filter(a=>(!f.stage||a.stage===f.stage)&&(!f.outcome||a.outcome===f.outcome)&&(!f.channel||a.channel===f.channel)&&(!f.status||(f.status==="active"?!a.outcome:!!a.outcome)));
  const filters=[["stage","Stage",D.stages],["outcome","Outcome",D.outcomes],["channel","Channel",D.channels],["status","Status",["active","closed"]]];
  return(<>
    <PageHeader title="Applications" actions={<Button variant="contained" onClick={()=>setCreating(true)}>New application</Button>}/>
    <div style={{display:"grid",gridTemplateColumns:mobile?"1fr 1fr":"repeat(4, minmax(0, 180px))",gap:mobile?12:16,marginBottom:20}}>{filters.map(([k,l,vals])=><TextField key={k} label={l} select size="small" shrink fullWidth value={f[k]} onChange={v=>setF({...f,[k]:v})} options={[{value:"",label:"Any"},...vals]}/>)}</div>
    <Count n={rows.length} one="application" many="applications"/>
    <DataGrid rows={rows} rowHeight={64} noRowsLabel={<EmptyState icon="work" title="No applications" text="Promote an offer from the inbox, or add one with New application."/>} columns={[
      {field:"role",headerName:"Role",flex:2.4,render:r=><TwoLine lead={<CompanyAvatar name={r.company_name}/>} primary={<Link onClick={e=>{e.preventDefault();onOpen(r.id);}} style={{fontWeight:500}}>{r.role}</Link>} secondary={<><span>{r.company_name}</span><Sep/><Meta icon={CHANNEL_ICONS[r.channel]}>{r.channel}</Meta></>}/>},
      {field:"stage",headerName:"Stage",width:mobile?140:150,render:r=><StageChip value={r.stage}/>},
      {field:"progress",headerName:"Progress",width:130,hideOnMobile:true,render:r=><StageProgress stage={r.stage} outcome={r.outcome}/>},
      {field:"outcome",headerName:"Outcome",width:150,hideOnMobile:true,render:r=><StageChip value={r.outcome}/>},
      {field:"priority",headerName:"Priority",width:120,render:r=><PriorityBars value={r.priority}/>,hideOnMobile:true},
      {field:"created_at",headerName:"Added",width:110,hideOnMobile:true,render:r=><RelDate value={r.created_at}/>}]}/>
    {creating&&<ApplicationDialog onClose={()=>setCreating(false)} onSave={a=>{setApplications(as=>[a,...as]);setCreating(false);}}/>}
  </>);
}
function ApplicationDialog({onClose,onSave}){const {Dialog,Button,TextField}=window.DS;const D=window.KIT_DATA;
  const[v,setV]=React.useState({company:"",role:"",channel:"portal",priority:"",stage:"evaluated"});const[err,setErr]=React.useState(false);const f=k=>x=>setV({...v,[k]:x});
  const save=()=>{if(!v.role||!v.company){setErr(true);return;}onSave({id:"a"+Date.now(),role:v.role,company_name:D.companies.find(c=>c.id===v.company).name,stage:v.stage,outcome:"",channel:v.channel,priority:v.priority,created_at:"Mar 5, 2026",url:"",notes:"",transitions:[{to_stage:v.stage,outcome:"",date:"Mar 5, 2026",note:""}]});};
  return <Dialog title="New application" onClose={onClose} actions={<><Button onClick={onClose}>Cancel</Button><Button variant="contained" onClick={save}>Create</Button></>}>
    <Stack><TextField label="Company" select fullWidth value={v.company} onChange={f("company")} options={D.companies.map(c=>({value:c.id,label:c.name}))} error={err&&!v.company} helperText={err&&!v.company?"Field required":undefined}/>
    <TextField label="Role" fullWidth value={v.role} onChange={f("role")} error={err&&!v.role} helperText={err&&!v.role?"Field required":undefined}/>
    <TextField label="Channel" select fullWidth value={v.channel} onChange={f("channel")} options={D.channels}/>
    <TextField label="Priority" select fullWidth shrink value={v.priority} onChange={f("priority")} options={[{value:"",label:"None"},"high","medium","low"]}/>
    <TextField label="URL" fullWidth/><TextField label="Notes" multiline minRows={3} fullWidth/>
    <TextField label="Stage" select fullWidth value={v.stage} onChange={f("stage")} options={["evaluated","applied"]}/>
    <TextField label="Start date" type="date" fullWidth helperText="When it entered that stage; empty means today"/></Stack></Dialog>;}
window.ApplicationsScreen=ApplicationsScreen;
