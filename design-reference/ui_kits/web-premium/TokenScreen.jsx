function TokenScreen({onDone}){
  const {Paper,TextField,Button}=window.DS;
  const[v,setV]=React.useState("");const[err,setErr]=React.useState("");const[loading,setLoading]=React.useState(false);
  const submit=(e)=>{e.preventDefault();if(!v){setErr("Enter the token");return;}setLoading(true);setTimeout(()=>{setLoading(false);if(v==="wrong")setErr("Invalid token");else onDone();},600);};
  return(<div style={{display:"grid",placeItems:"center",minHeight:"100vh",padding:16}}>
    <Paper as="form" onSubmit={submit} noValidate padding={32} style={{width:"100%",maxWidth:400,boxShadow:"var(--shadow-dialog)"}}>
      <h1 style={{margin:"0 0 6px",fontFamily:"var(--font-heading)",fontSize:"2rem",fontWeight:500,lineHeight:1.15,letterSpacing:"-0.015em"}}>Job Offer Funnel</h1>
      <p style={{margin:"0 0 24px",color:"var(--text-secondary)"}}>Enter the API token (AUTH_TOKEN) to continue.</p>
      <TextField label="Token" type="password" fullWidth autoFocus value={v} onChange={x=>{setV(x);setErr("");}} error={!!err} helperText={err} style={{marginBottom:20}}/>
      <Button type="submit" variant="contained" fullWidth loading={loading}>Continue</Button>
    </Paper>
  </div>);
}
window.TokenScreen=TokenScreen;
