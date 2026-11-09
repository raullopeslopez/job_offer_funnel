function SettingsScreen(){
  const {Tabs,Button,IconButton,DataGrid,Dialog,TextField}=window.DS;const D=window.KIT_DATA;
  const[s,setS]=React.useState("companies");const[dialog,setDialog]=React.useState(null);const close=()=>setDialog(null);
  const act=r=><span className="row-actions" style={{display:"flex",gap:2,marginLeft:"auto"}}><IconButton size="small" icon="edit" label={"Edit “"+r.name+"”"} onClick={()=>setDialog({type:"edit",row:r})}/><IconButton size="small" icon="delete_outline" label={"Delete “"+r.name+"”"} onClick={()=>setDialog({type:"delete",row:r})}/></span>;
  const comp=s==="companies";
  return(<>
    <H1>Settings</H1>
    <Tabs value={s} onChange={setS} style={{marginBottom:16}} tabs={[{value:"companies",label:<TabLabel label="Companies" n={D.companies.length}/>},{value:"job-boards",label:<TabLabel label="Job boards" n={D.jobBoards.length}/>}]}/>
    <div style={{display:"flex",justifyContent:"flex-end",marginBottom:16}}><Button variant="contained" onClick={()=>setDialog({type:"edit",row:null})}>{comp?"New company":"New job board"}</Button></div>
    {comp?<DataGrid rows={D.companies} rowHeight={60} noRowsLabel={<EmptyState icon="domain" title="No companies"/>} columns={[{field:"name",headerName:"Company",flex:2,render:r=><TwoLine lead={<CompanyAvatar name={r.name} domain={r.website}/>} primary={r.name} secondary={<Meta icon="language">{r.website||"—"}</Meta>}/>},{field:"a",headerName:"",width:96,render:act}]}/>
    :<DataGrid rows={D.jobBoards} rowHeight={60} noRowsLabel={<EmptyState icon="travel_explore" title="No job boards"/>} columns={[{field:"name",headerName:"Job board",render:r=><TwoLine lead={<CompanyAvatar name={r.name}/>} primary={r.name} secondary={<Meta icon="code">{r.syntax}</Meta>}/>},{field:"search_url_template",headerName:"Search URL template",flex:3,hideOnMobile:true,render:r=><span style={{fontFamily:"var(--font-mono)",fontSize:12.5,color:"var(--text-secondary)",overflow:"hidden",textOverflow:"ellipsis"}}>{r.search_url_template}</span>},{field:"a",headerName:"",width:96,render:act}]}/>}
    {dialog&&dialog.type==="delete"&&<ConfirmDialog danger title={"Delete “"+dialog.row.name+"”"} text={comp?"The company will be deleted.":"The job board and its generated searches will be deleted."} verb="Delete" onClose={close} onConfirm={close}/>}
    {dialog&&dialog.type==="edit"&&<Dialog title={dialog.row?"Edit “"+dialog.row.name+"”":comp?"New company":"New job board"} onClose={close} actions={<><Button onClick={close}>Cancel</Button><Button variant="contained" onClick={close}>{dialog.row?"Save":"Create"}</Button></>}>
      <Stack><TextField label="Name" fullWidth defaultValue={dialog.row?.name}/>{comp?<TextField label="Website" fullWidth defaultValue={dialog.row?.website}/>:<><TextField label="Search URL template" fullWidth defaultValue={dialog.row?.search_url_template} helperText="Use {query} and {location}"/><TextField label="Syntax" select fullWidth defaultValue={dialog.row?.syntax??"boolean"} options={["boolean","minus","keywords"]}/></>}</Stack></Dialog>}
  </>);
}
window.SettingsScreen=SettingsScreen;
