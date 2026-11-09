const NAV=[{path:"/",label:"Home",icon:"home"},{path:"/inbox",label:"Inbox",icon:"inbox"},{path:"/searches",label:"Searches",icon:"travel_explore"},{path:"/watched-companies",label:"Watched companies",icon:"visibility"},{path:"/applications",label:"Applications",icon:"work"},{path:"/metrics",label:"Metrics",icon:"insights"},{path:"/settings",label:"Settings",icon:"settings"}];
function useWidth(){const[w,setW]=React.useState(window.innerWidth);React.useEffect(()=>{const f=()=>setW(window.innerWidth);window.addEventListener("resize",f);return()=>window.removeEventListener("resize",f);},[]);return w;}
function App(){
  const {SideNav,Snackbar,Button,AppBar,IconButton}=window.DS;
  const width=useWidth();const mobile=width<900;
  const[theme,setTheme]=React.useState(localStorage.getItem("jof-premium-theme")||(window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches?"premium-dark":"premium"));
  React.useEffect(()=>{document.documentElement.setAttribute("data-theme",theme);localStorage.setItem("jof-premium-theme",theme);},[theme]);
  const[authed,setAuthed]=React.useState(!location.search.includes("token"));
  const[path,setPath]=React.useState(localStorage.getItem("jof-premium-path")||"/inbox");
  const[detail,setDetail]=React.useState(null);const[navOpen,setNavOpen]=React.useState(false);
  const[offers,setOffers]=React.useState(window.KIT_DATA.offers);
  const[apps,setApps]=React.useState(window.KIT_DATA.applications);
  const[notice,setNotice]=React.useState(null);
  React.useEffect(()=>{localStorage.setItem("jof-premium-path",path);},[path]);
  React.useEffect(()=>{if(!notice)return;const t=setTimeout(()=>setNotice(null),6000);return()=>clearTimeout(t);},[notice]);
  const notify=(message,undo)=>setNotice({message,undo});
  const dark=theme==="premium-dark";
  const toggle=<IconButton icon={dark?"light_mode":"dark_mode"} label={dark?"Light theme":"Dark theme"} onClick={()=>setTheme(dark?"premium":"premium-dark")}/>;
  if(!authed)return(<><div style={{position:"fixed",top:12,right:12}}>{toggle}</div><TokenScreen onDone={()=>setAuthed(true)}/></>);
  const go=p=>{setPath(p);setDetail(null);window.scrollTo(0,0);};
  const move=(id,patch)=>setApps(as=>as.map(a=>a.id!==id?a:{...a,stage:patch.stage||a.stage,outcome:patch.outcome||a.outcome,transitions:[...a.transitions,{to_stage:patch.stage||a.stage,outcome:patch.outcome||"",date:"Mar 5, 2026",note:""}]}));
  const undo=id=>{setApps(as=>as.map(a=>{if(a.id!==id||a.transitions.length<2)return a;const tr=a.transitions.slice(0,-1);const last=tr[tr.length-1];return{...a,transitions:tr,stage:last.to_stage,outcome:last.outcome};}));notify("Last transition undone");};
  let page;
  if(path==="/")page=<div style={{paddingTop:mobile?8:40,maxWidth:640}}><h1 style={{margin:"0 0 12px",fontFamily:"var(--font-heading)",fontSize:mobile?"2.25rem":"3rem",fontWeight:500,lineHeight:1.08,letterSpacing:"-0.02em"}}>Job Offer Funnel</h1><p style={{margin:0,color:"var(--text-secondary)",fontSize:"1.0625rem"}}>Your job search as a funnel, from the first offer to the last interview.</p></div>;
  else if(path==="/inbox")page=<InboxScreen offers={offers} setOffers={setOffers} notify={notify}/>;
  else if(path==="/searches")page=<SearchesScreen notify={notify}/>;
  else if(path==="/watched-companies")page=<WatchedScreen notify={notify}/>;
  else if(path==="/applications"){const a=detail&&apps.find(x=>x.id===detail);page=a?<ApplicationDetailScreen mobile={mobile} application={a} onBack={()=>setDetail(null)} onMove={move} onUndo={undo} onDelete={id=>{setApps(as=>as.filter(x=>x.id!==id));setDetail(null);}} notify={notify}/>:<ApplicationsScreen mobile={mobile} applications={apps} setApplications={setApps} onOpen={setDetail}/>;}
  else if(path==="/metrics")page=<MetricsScreen mobile={mobile}/>;
  else page=<SettingsScreen/>;
  const navFooter=<div style={{display:"flex",alignItems:"center",justifyContent:"space-between",color:"var(--text-secondary)",fontSize:"var(--body2-size)"}}><span>{dark?"Dark theme":"Light theme"}</span>{toggle}</div>;
  return(<div style={{display:"flex",minHeight:"100vh",background:"var(--bg-default)",color:"var(--text-primary)"}}>
    {!mobile&&<SideNav items={NAV} active={path} onNavigate={go} footer={navFooter} style={{position:"sticky",top:0,height:"100vh",minHeight:0,alignSelf:"flex-start"}}/>}
    <div style={{flex:1,minWidth:0}}>
      {mobile&&<AppBar leading={<IconButton icon="menu" label="Open navigation" onClick={()=>setNavOpen(true)}/>} trailing={toggle}/>}
      <main style={{padding:mobile?"20px 16px 96px":"40px 48px 96px",maxWidth:1280,boxSizing:"border-box"}}>{page}</main>
    </div>
    {mobile&&<SideNav variant="temporary" open={navOpen} onClose={()=>setNavOpen(false)} items={NAV} active={path} onNavigate={go} footer={navFooter}/>}
    <Snackbar open={!!notice} message={notice&&notice.message} action={notice&&notice.undo&&<Button color="inherit" size="small" onClick={()=>{notice.undo();setNotice(null);}}>Undo</Button>}/>
  </div>);
}
ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
