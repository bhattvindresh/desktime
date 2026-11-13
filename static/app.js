const $ = id => document.getElementById(id);
let activeSession = null, timerInterval = null;
const socket = io();
const pad = n => String(n).padStart(2, "0");
function duration(seconds) { seconds = Math.max(0, Math.floor(seconds)); return `${pad(Math.floor(seconds/3600))}:${pad(Math.floor(seconds%3600/60))}:${pad(seconds%60)}`; }
function elapsed() { return activeSession ? Math.floor((Date.now() - new Date(activeSession.started_at).getTime())/1000) : 0; }
function tick() { $("timer").textContent = duration(elapsed()); }
async function load() {
  const [meRes, sumRes] = await Promise.all([fetch("/api/me"), fetch("/api/summary")]);
  const me = await meRes.json(), data = await sumRes.json();
  activeSession = me.active;
  $("totalTime").textContent = duration(data.total_seconds);
  $("activeCount").textContent = data.active_count;
  $("timerStatus").textContent = activeSession ? "Tracking" : "Not tracking";
  $("timerStatus").className = activeSession ? "pill active" : "pill";
  $("toggleBtn").textContent = activeSession ? "■ Stop tracking" : "▶ Start tracking";
  $("toggleBtn").className = activeSession ? "danger full" : "primary full";
  tick(); render(data.sessions);
}
function render(sessions) {
  $("sessionRows").innerHTML = sessions.map(s => `<tr><td>${escapeHtml(s.employee)}</td><td>${escapeHtml(s.activity)}</td><td>${new Date(s.started_at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</td><td>${duration(s.seconds)}</td><td><span class="status ${s.ended_at ? "done" : "working"}">${s.ended_at ? "Completed" : "Working"}</span></td></tr>`).join("") || '<tr><td colspan="5">No sessions yet.</td></tr>';
  $("activityList").innerHTML = sessions.slice(0,5).map(s => `<div class="activity-item"><span class="activity-icon">◷</span><div><b>${escapeHtml(s.activity)}</b><small>${escapeHtml(s.employee)} · ${new Date(s.started_at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</small></div><strong>${duration(s.seconds)}</strong></div>`).join("") || '<p class="muted">No activity recorded today.</p>';
}
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
$("toggleBtn").addEventListener("click", async () => {
  const starting = !activeSession;
  const response = await fetch(starting ? "/api/start" : "/api/stop", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: starting ? JSON.stringify({activity:$("activity").value.trim() || "General work"}) : "{}"
  });
  const result = await response.json();
  if (!response.ok) { alert(result.error || "Something went wrong"); return; }
  await load();
});
socket.on("session_update", () => load());
socket.on("connect", () => { $("timerStatus").title = "Connected to live server"; });
load();
setInterval(tick, 1000);
setInterval(load, 15000);
