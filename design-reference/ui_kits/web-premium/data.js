window.KIT_DATA={
offers:[
{id:"o1",title:"Senior Python Developer",company:"Acme Robotics",source:"remoteok",created_at:"Mar 4, 2026",status:"pending",url:"#"},
{id:"o2",title:"Backend Engineer (FastAPI)",company:"Northwind",source:"LinkedIn",created_at:"Mar 3, 2026",status:"pending",url:"#"},
{id:"o3",title:"Platform Engineer",company:"Globex",source:"himalayas",created_at:"Mar 2, 2026",status:"pending",url:"#"},
{id:"o4",title:"Data Engineer",company:"Initech",source:"remotive",created_at:"Feb 28, 2026",status:"pending",url:"#"},
{id:"o5",title:"Python Developer (Django)",company:"Umbrella",source:"jobicy",created_at:"Feb 27, 2026",status:"discarded",discard_reason:"On-site only",url:"#"},
{id:"o6",title:"Staff Software Engineer",company:"Hooli",source:"LinkedIn",created_at:"Feb 25, 2026",status:"promoted",url:"#"}],
applications:[
{id:"a1",role:"Backend Engineer",company_name:"Northwind",stage:"interviewing",outcome:"",channel:"referral",priority:"high",created_at:"Feb 12, 2026",url:"https://careers.northwind.example/backend",notes:"Referred by Marta. Team works on billing.",transitions:[{to_stage:"evaluated",outcome:"",date:"Feb 12, 2026",note:""},{to_stage:"applied",outcome:"",date:"Feb 13, 2026",note:"Sent CV v3"},{to_stage:"screening",outcome:"",date:"Feb 20, 2026",note:"Call with recruiter"},{to_stage:"interviewing",outcome:"",date:"Mar 1, 2026",note:"Tech interview scheduled"}]},
{id:"a2",role:"Staff Software Engineer",company_name:"Hooli",stage:"evaluated",outcome:"",channel:"portal",priority:"medium",created_at:"Feb 25, 2026",url:"",notes:"",transitions:[{to_stage:"evaluated",outcome:"",date:"Feb 25, 2026",note:""}]},
{id:"a3",role:"Python Developer",company_name:"Acme Robotics",stage:"screening",outcome:"ghosted",channel:"recruiter_inbound",priority:"low",created_at:"Jan 30, 2026",url:"",notes:"",transitions:[{to_stage:"evaluated",outcome:"",date:"Jan 30, 2026",note:""},{to_stage:"applied",outcome:"",date:"Jan 31, 2026",note:""},{to_stage:"screening",outcome:"",date:"Feb 5, 2026",note:""},{to_stage:"screening",outcome:"ghosted",date:"Feb 26, 2026",note:"No reply in 3 weeks"}]},
{id:"a4",role:"Senior Backend Developer",company_name:"Globex",stage:"applied",outcome:"",channel:"direct",priority:"high",created_at:"Feb 18, 2026",url:"",notes:"",transitions:[{to_stage:"evaluated",outcome:"",date:"Feb 18, 2026",note:""},{to_stage:"applied",outcome:"",date:"Feb 19, 2026",note:""}]}],
stages:["evaluated","applied","screening","interviewing","offer","accepted"],
outcomes:["rejected","ghosted","withdrawn","offer_declined"],
channels:["portal","referral","recruiter_inbound","direct","networking"],
conversion:[{from:"evaluated",to:"applied",rf:10,rt:8,rate:80},{from:"applied",to:"screening",rf:8,rt:3,rate:37.5},{from:"screening",to:"interviewing",rf:3,rt:2,rate:66.7},{from:"interviewing",to:"offer",rf:2,rt:0,rate:0},{from:"offer",to:"accepted",rf:0,rt:0,rate:null}],
pipeline:[{stage:"evaluated",n:2},{stage:"applied",n:5},{stage:"screening",n:1},{stage:"interviewing",n:2},{stage:"offer",n:0}],
companies:[{id:"c1",name:"Acme Robotics",website:"acme.example"},{id:"c2",name:"Globex",website:"globex.example"},{id:"c3",name:"Northwind",website:"northwind.example"}],
jobBoards:[{id:"j1",name:"LinkedIn",syntax:"boolean",search_url_template:"https://www.linkedin.com/jobs/search/?keywords={query}&location={location}"},{id:"j2",name:"InfoJobs",syntax:"keywords",search_url_template:"https://www.infojobs.net/jobsearch/search-results/list.xhtml?keyword={query}"},{id:"j3",name:"Indeed",syntax:"minus",search_url_template:"https://es.indeed.com/jobs?q={query}&l={location}"}],
profiles:[{id:"p1",name:"Remote Python",titles:["Python Developer","Backend Engineer"],keywords:["python"],excluded_keywords:["php","wordpress"],location:"Spain",work_modes:["remote"]},{id:"p2",name:"Madrid platform",titles:["Platform Engineer","DevOps Engineer"],keywords:["kubernetes"],excluded_keywords:[],location:"Madrid",work_modes:["hybrid","onsite"]}],
watched:[{id:"w1",name:"Acme Robotics",ats:"greenhouse",board:"acmerobotics"},{id:"w2",name:"Globex",ats:"lever",board:"globex"},{id:"w3",name:"Northwind",ats:"ashby",board:"northwind"}],
feeds:["remoteok","remotive","himalayas","jobicy"]
};
