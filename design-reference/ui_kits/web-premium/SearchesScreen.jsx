function SearchesScreen({notify}){
  const {PageHeader,Button,IconButton,DataGrid,Dialog,TextField,Link}=window.DS;const D=window.KIT_DATA;
  const[profiles,setProfiles]=React.useState(D.profiles);const[dialog,setDialog]=React.useState(null);const close=()=>setDialog(null);
  const j=v=>v.join(", ");
  const MODE_ICONS={remote:"home_work",hybrid:"sync_alt",onsite:"apartment"};
  return(<>
    <PageHeader title="Searches" actions={<Button variant="contained" onClick={()=>setDialog({type:"edit",profile:null})}>New profile</Button>}/>
    <Muted style={{marginBottom:16}}>Each search profile builds the search for every job board.</Muted>
    <DataGrid rows={profiles} rowHeight={64} noRowsLabel={<EmptyState icon="manage_search" title="No profiles" text="A profile turns titles and keywords into a search for every job board."/>} columns={[
      {field:"name",headerName:"Profile",flex:1.6,render:r=><TwoLine lead={<IconTile name="manage_search" tone="indigo"/>} primary={r.name} secondary={<><Meta icon="place">{r.location||"—"}</Meta>{r.work_modes.length>0&&<><Sep/><Meta icon={MODE_ICONS[r.work_modes[0]]}>{j(r.work_modes)}</Meta></>}</>}/>},
      {field:"titles",headerName:"Titles",flex:2,render:r=><span style={{overflow:"hidden",textOverflow:"ellipsis"}}>{j(r.titles)}</span>,hideOnMobile:true},
      {field:"keywords",headerName:"Keywords",render:r=><Tokens items={r.keywords}/>,hideOnMobile:true},
      {field:"excluded_keywords",headerName:"Excluded",render:r=><Tokens items={r.excluded_keywords} excluded/>,hideOnMobile:true},
      {field:"a",headerName:"",width:180,mobileWidth:170,render:r=><Actions><Button size="small" onClick={()=>setDialog({type:"searches",profile:r})}>Searches</Button><span className="row-actions" style={{display:"flex",gap:2}}><IconButton size="small" icon="edit" label={"Edit “"+r.name+"”"} onClick={()=>setDialog({type:"edit",profile:r})}/><IconButton size="small" icon="delete_outline" label={"Delete “"+r.name+"”"} onClick={()=>setDialog({type:"delete",profile:r})}/></span></Actions>}]}/>
    {dialog&&dialog.type==="edit"&&<ProfileDialog profile={dialog.profile} onClose={close} onSave={(p)=>{setProfiles(ps=>dialog.profile?ps.map(x=>x.id===p.id?p:x):[...ps,p]);close();}}/>}
    {dialog&&dialog.type==="delete"&&<ConfirmDialog danger title={"Delete “"+dialog.profile.name+"”"} text="The profile and its generated searches will be deleted." verb="Delete" onClose={close} onConfirm={()=>{setProfiles(ps=>ps.filter(x=>x.id!==dialog.profile.id));close();}}/>}
    {dialog&&dialog.type==="searches"&&<Dialog maxWidth={900} title={"Searches for “"+dialog.profile.name+"”"} onClose={close} actions={<Button onClick={close}>Close</Button>}>
      <div style={{display:"grid",gap:24}}>
        {dialog.profile.work_modes.length>0&&<Muted style={{margin:0}}>Filter by work mode: {j(dialog.profile.work_modes)}</Muted>}
        {D.jobBoards.map(b=><section key={b.id}><h3 style={{margin:0,display:"flex",alignItems:"center",gap:10,fontFamily:"var(--font-heading)",fontSize:"var(--h6-size)",fontWeight:500}}><CompanyAvatar name={b.name} size={24}/>{b.name}</h3>
          <ul style={{margin:"8px 0",paddingLeft:16,display:"grid",gap:8}}>{dialog.profile.titles.map(t=><li key={t}><Link href="#" external>{b.syntax==="boolean"?'"'+t+'" AND '+dialog.profile.keywords.join(" AND ")+(dialog.profile.excluded_keywords.length?" NOT ("+dialog.profile.excluded_keywords.join(" OR ")+")":""):b.syntax==="minus"?t+" "+dialog.profile.keywords.join(" ")+" "+dialog.profile.excluded_keywords.map(x=>"-"+x).join(" "):t+" "+dialog.profile.keywords.join(" ")}</Link></li>)}</ul></section>)}
      </div></Dialog>}
  </>);
}
function ProfileDialog({profile,onClose,onSave}){const {Dialog,Button,TextField}=window.DS;
  const[v,setV]=React.useState({name:profile?.name??"",titles:profile?.titles.join(", ")??"",keywords:profile?.keywords.join(", ")??"",excluded:profile?.excluded_keywords.join(", ")??"",location:profile?.location??"",work_modes:profile?.work_modes??[]});
  const[err,setErr]=React.useState(false);const f=k=>x=>setV({...v,[k]:x});const L=s=>s.trim()?s.split(",").map(x=>x.trim()):[];
  const save=()=>{if(!v.name){setErr(true);return;}onSave({id:profile?.id??"p"+Date.now(),name:v.name,titles:L(v.titles),keywords:L(v.keywords),excluded_keywords:L(v.excluded),location:v.location,work_modes:v.work_modes});};
  return <Dialog title={profile?"Edit “"+profile.name+"”":"New profile"} onClose={onClose} actions={<><Button onClick={onClose}>Cancel</Button><Button variant="contained" onClick={save}>{profile?"Save":"Create"}</Button></>}>
    <Stack><TextField label="Name" fullWidth value={v.name} onChange={x=>{f("name")(x);setErr(false);}} error={err} helperText={err?"Field required":undefined}/>
    <TextField label="Titles" fullWidth value={v.titles} onChange={f("titles")} helperText="Separated by commas; any of them may match"/>
    <TextField label="Keywords" fullWidth value={v.keywords} onChange={f("keywords")} helperText="Separated by commas; all of them must appear"/>
    <TextField label="Excluded keywords" fullWidth value={v.excluded} onChange={f("excluded")} helperText="Separated by commas; none of them may appear"/>
    <TextField label="Location" fullWidth value={v.location} onChange={f("location")}/>
    <TextField label="Work modes" select fullWidth value={v.work_modes} onChange={f("work_modes")} options={["remote","hybrid","onsite"]} helperText="None means any"/></Stack></Dialog>;}
window.SearchesScreen=SearchesScreen;
