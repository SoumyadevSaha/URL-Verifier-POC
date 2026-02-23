// backend/app/static/ui.js
async function refreshJobs() {
  const res = await fetch("/jobs");
  const jobs = await res.json();
  const root = document.getElementById("jobs");
  root.innerHTML = "";
  jobs.forEach(j => {
    const d = document.createElement("div");
    d.className = "job";
    const time = new Date(j.created_at).toLocaleString();
    d.innerHTML = `<b>${j.url}</b> <span class="small">[${j.status}]</span><br/>
                   <span class="small">created: ${time}</span><br/>
                   <div style="margin-top:8px">
                     <a href="/jobs/${j.id}">details</a> |
                     <a href="/jobs/${j.id}/logs">logs</a> |
                     <a href="/artifacts/${j.id}/screenshot.png" target="_blank">screenshot</a>
                   </div>
                 `;
    root.appendChild(d);
  });
}

async function createJob(){
  const url = document.getElementById("urlInput").value;
  document.getElementById("msg").innerText = "Submitting...";
  try {
    const res = await fetch("/analyze", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url})});
    const j = await res.json();
    document.getElementById("msg").innerText = "Submitted: " + j.job_id;
    refreshJobs();
  } catch(e) {
    document.getElementById("msg").innerText = "Error: " + e;
  }
}