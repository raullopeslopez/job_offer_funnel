function WatchedScreen({notify}){
  const {PageHeader,Button,IconButton,DataGrid,Dialog,TextField,Alert}=window.DS;const D=window.KIT_DATA;
  const[rows,setRows]=React.useState(D.watched);const[dialog,setDialog]=React.useState(null);const close=()=>setDialog(null);
  return(<>
    <PageHeader title="Watched companies" actions={<Button variant="contained" onClick={()=>setDialog({type:"watch"})}>Watch a company</Button>}/>
    <DataGrid hideFooter rows={rows} rowHeight={64} noRowsLabel={<EmptyState icon="visibility" title="No watched companies" text="Watch a company to import offers straight from its careers page."/>} columns={[
      {field:"name",headerName:"Company",flex:2,render:r=><TwoLine lead={<CompanyAvatar name={r.name}/>} primary={r.name} secondary={<><Meta icon="hub">{r.ats}</Meta><Sep/><Meta mono>{r.board||"—"}</Meta></>}/>},
      {field:"a",headerName:"",width:150,mobileWidth:130,render:r=><Actions><Button size="small" onClick={()=>setDialog({type:"import",c:r})}>Import</Button><span className="row-actions"><IconButton size="small" icon="visibility_off" label={"Stop watching “"+r.name+"”"} onClick={()=>setDialog({type:"stop",c:r})}/></span></Actions>}]}/>
    {dialog&&dialog.type==="watch"&&<WatchDialog onClose={close} onWatch={c=>{setRows(rs=>[...rs,c].sort((a,b)=>a.name.localeCompare(b.name)));close();}}/>}
    {dialog&&dialog.type==="stop"&&<ConfirmDialog danger title={"Stop watching “"+dialog.c.name+"”?"} text="Its offers already in the inbox are kept." verb="Stop watching" onClose={close} onConfirm={()=>{setRows(rs=>rs.filter(x=>x.id!==dialog.c.id));close();}}/>}
    {dialog&&dialog.type==="import"&&<ImportWatchedDialog company={dialog.c} onClose={close}/>}
  </>);
}
function WatchDialog({onClose,onWatch}){const {Dialog,Button,TextField}=window.DS;const[n,setN]=React.useState("");const[ats,setAts]=React.useState("greenhouse");const[b,setB]=React.useState("");const[err,setErr]=React.useState(false);
  return <Dialog title="Watch a company" onClose={onClose} actions={<><Button onClick={onClose}>Cancel</Button><Button variant="contained" onClick={()=>{if(!n){setErr(true);return;}onWatch({id:"w"+Date.now(),name:n,ats,board:b});}}>Watch</Button></>}>
    <Stack><TextField label="Name" fullWidth value={n} onChange={x=>{setN(x);setErr(false);}} error={err} helperText={err?"Field required":undefined}/><TextField label="ATS" select fullWidth value={ats} onChange={setAts} options={["greenhouse","lever","ashby"]}/><TextField label="Board" fullWidth value={b} onChange={setB} helperText="The company's name in its careers URL, e.g. boards.greenhouse.io/acme"/></Stack></Dialog>;}
function ImportWatchedDialog({company,onClose}){const {Dialog,Button,TextField,Alert}=window.DS;const[p,setP]=React.useState("");const[done,setDone]=React.useState(false);
  return <Dialog title={"Import “"+company.name+"”"} onClose={onClose} actions={<><Button onClick={onClose}>Close</Button><Button variant="contained" onClick={()=>p&&setDone(true)}>Import</Button></>}>
    <Stack>{done&&<Alert severity="success">14 found, 3 matching, 3 added, 0 already in the inbox, 0 expired</Alert>}<TextField label="Search profile" select fullWidth value={p} onChange={setP} options={window.KIT_DATA.profiles.map(x=>({value:x.id,label:x.name}))}/></Stack></Dialog>;}
window.WatchedScreen=WatchedScreen;
