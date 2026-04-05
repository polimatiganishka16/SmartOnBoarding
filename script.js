
let step=1,last=Date.now();

function next(){
 step++;
 track("next");
 document.getElementById("step").innerText="Step "+step;
 document.getElementById("bar").style.width=Math.min(step*20,100)+"%";
}

function complete(){
 track("task_completed");
 alert("Done 🎉");
 location="/dashboard";
}

function track(a){
 fetch('/track',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:a})});
 last=Date.now();
}

setInterval(()=>{
 if(Date.now()-last>10000){
  document.getElementById("help").style.display="block";
  track("inactive");
 }
},2000);

setInterval(()=>{
 fetch('/recommend').then(r=>r.json()).then(d=>{
  document.getElementById("ai").innerText="AI: "+d.msg;
 });
},5000);

fetch('/ab-test').then(r=>r.json()).then(d=>{
 if(d.variant==="B"){
  document.getElementById("variant").innerText="🚀 Quick Mode";
 }
});
