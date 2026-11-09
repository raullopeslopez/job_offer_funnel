function ApplicationDetailScreen({application:a,onBack,onMove,onUndo,onDelete,notify,mobile}){
  const {Link,Button,FieldList,Dialog,TextField,StageChip,Paper,PageHeader}=window.DS;const D=window.KIT_DATA;
  const[dialog,setDialog]=React.useState(null);const[target,setTarget]=React.useState("");const close=()=>setDialog(null);
  const moving=dialog==="move";
  return(<>
    <PageHeader eyebrow={<Link onClick={e=>{e.preventDefault();onBack();}} style={{fontSize:"var(--body2-size)",display:"inline-flex",alignItems:"center",gap:4}}><Icon name="arrow_back" size={16}/>Back to applications</Link>} title={a.role} actions={<><Button variant="outlined" onClick={()=>setDialog("edit")}>Edit</Button><Button color="error" onClick={()=>setDialog("delete")}>Delete</Button></>} style={{marginBottom:8}}/>
    <div style={{display:"flex",alignItems:"center",gap:10,margin:"0 0 24px"}}><CompanyAvatar name={a.company_name} size={28}/><p style={{margin:0,fontFamily:"var(--font-heading)",fontSize:"var(--h6-size)",fontWeight:400,color:"var(--text-secondary)"}}>at {a.company_name}</p></div>
    <Paper padding={mobile?16:20} style={{marginBottom:28,display:"flex",alignItems:"center",gap:16,flexWrap:"wrap"}}>
      <div style={{flex:"1 1 260px",display:"grid",gap:10}}>
        <div style={{display:"flex",alignItems:"center",gap:8,flexWrap:"wrap",color:"var(--text-secondary)"}}>
          {a.outcome?<><span style={{whiteSpace:"nowrap"}}>Closed as</span><StageChip value={a.outcome}/><span style={{whiteSpace:"nowrap"}}>in stage</span><StageChip value={a.stage}/></>:<><span style={{whiteSpace:"nowrap"}}>In stage</span><StageChip value={a.stage} size="medium"/></>}
        </div>
        <StageProgress stage={a.stage} outcome={a.outcome} segment={mobile?28:40} height={6}/>
      </div>
      <Row><Button variant="contained" onClick={()=>{setTarget("");setDialog("move");}}>Move</Button><Button variant="outlined" onClick={()=>{setTarget("");setDialog("close");}}>Close</Button><Button onClick={()=>setDialog("undo")}>Undo last transition</Button></Row>
    </Paper>
    <div style={{display:"grid",gridTemplateColumns:mobile?"minmax(0,1fr)":"minmax(280px,1fr) minmax(0,1.6fr)",gap:28,alignItems:"start"}}>
      <section style={{minWidth:0}}><H2>Details</H2><Paper padding={20}><FieldList items={[{label:"Channel",icon:"alt_route",value:a.channel&&<Meta icon={CHANNEL_ICONS[a.channel]}>{a.channel}</Meta>},{label:"Priority",icon:"flag",value:a.priority&&<PriorityBars value={a.priority}/>},{label:"URL",icon:"link",value:a.url&&<Link href={a.url} external>{a.url}</Link>},{label:"Notes",icon:"notes",value:a.notes},{label:"Added",icon:"event",value:a.created_at&&<span style={{fontVariantNumeric:"tabular-nums"}}>{a.created_at}</span>}]}/></Paper></section>
      <section style={{minWidth:0}}><H2>History</H2><Paper padding={mobile?16:20}><Timeline transitions={a.transitions}/></Paper></section>
    </div>
    {(dialog==="move"||dialog==="close")&&<Dialog title={(moving?"Move":"Close")+" “"+a.role+"”"} onClose={close} actions={<><Button onClick={close}>Cancel</Button><Button variant="contained" onClick={()=>{if(target){onMove(a.id,moving?{stage:target}:{outcome:target});notify(moving?"Application moved":"Application closed");}close();}}>{moving?"Move":"Close"}</Button></>}>
      <Stack><TextField label={moving?"Stage":"Outcome"} select fullWidth value={target} onChange={setTarget} options={moving?D.stages:D.outcomes}/><TextField label="Date" type="date" fullWidth helperText="Empty means today"/><TextField label="Note" multiline minRows={2} fullWidth/></Stack></Dialog>}
    {dialog==="undo"&&<ConfirmDialog title={"Undo the last transition of “"+a.role+"”?"} text="The application returns to where it was before it, and the transition leaves the history." verb="Undo" onClose={close} onConfirm={()=>{onUndo(a.id);close();}}/>}
    {dialog==="delete"&&<ConfirmDialog danger title={"Delete “"+a.role+"”?"} text="Its history will be deleted too." verb="Delete" onClose={close} onConfirm={()=>{close();onDelete(a.id);}}/>}
    {dialog==="edit"&&<Dialog title={"Edit “"+a.role+"”"} onClose={close} actions={<><Button onClick={close}>Cancel</Button><Button variant="contained" onClick={close}>Save</Button></>}><Stack><TextField label="Role" fullWidth defaultValue={a.role}/><TextField label="Channel" select fullWidth defaultValue={a.channel} options={D.channels}/><TextField label="Priority" select fullWidth shrink defaultValue={a.priority} options={[{value:"",label:"None"},"high","medium","low"]}/><TextField label="URL" fullWidth defaultValue={a.url}/><TextField label="Notes" multiline minRows={3} fullWidth defaultValue={a.notes}/></Stack></Dialog>}
  </>);
}
window.ApplicationDetailScreen=ApplicationDetailScreen;
