import {buildOffice, ROLE_COLORS} from "./scene.js";

const $ = selector => document.querySelector(selector);
const labels = {
  idle:"Idle", working:"Working", queued:"Queued", review:"Review", blocked:"Blocked",
  done:"Done", failed:"Failed", interrupted:"Interrupted", stale:"Update due"
};
const rank={working:0,blocked:1,review:2,queued:3,stale:4,failed:5,interrupted:6,done:7};
const attention=new Set(["blocked","review","stale","failed","interrupted"]);
const groups=["In progress","Needs attention","Queued","Available","Available specialists"];
const demoBrief = [
  ["Customer Researcher","working","Reviewing commuter feedback and recurring objections."],
  ["Competitor Researcher","working","Comparing leading offers, packs, and warranties."],
  ["Evidence Reviewer","queued","Ready to check the evidence once research is complete."],
  ["Ad Strategist","queued","Waiting for reviewed evidence before drafting test angles."],
  ["Video Editor","review","A vertical storyboard preview is ready to review."]
];
const formatTime = new Intl.DateTimeFormat(undefined,{hour:"numeric",minute:"2-digit"});
const EMPTY={roles:{},history:[]};
let catalog, office, selected, filter="all", demo=false, connected=false;
let latest=EMPTY, lastPayload="", demoSnapshot;

function node(tag,text,className) {
  const element=document.createElement(tag);
  if (text) element.textContent=text;
  if (className) element.className=className;
  return element;
}

function badge(status) {
  return node("span",labels[status] || status,`badge ${status}`);
}

function showMessage(message) {
  const box=$("#office-message");
  box.textContent=message;
  box.hidden=!message;
}

function makeDemo() {
  const items=demoBrief.map(([role,status,note],i)=>({
    role,status,note,product:i===4?"Travel organizer":"Commuter bottle",
    title:i===4?"Render storyboard preview":"Market Research Team sprint",
    record:i===4?"demo-preview":"demo-research",
    updated:new Date().toISOString()
  }));
  return {roles:Object.fromEntries(items.map(item=>[item.role,[item]])),history:items};
}

function setConnection() {
  const wrapper=$("#connection");
  wrapper.className=`connection ${demo ? "demo" : connected ? "live" : "offline"}`;
  wrapper.querySelector("span").textContent=demo ? "Demo data" : connected ? "Live on this Mac" : "Disconnected";
}

function choose(name) {
  selected=selected===name ? undefined : name;
  render();
}

function recordLink(record) {
  const parts=record.split("/");
  const selectedRun=parts[2]?.includes("-skill-run-");
  return {
    title:selectedRun?"Open report":"Open task record",
    href:selectedRun?"/workflows?run="+encodeURIComponent(parts.slice(1,-1).join("/")):
      "/" + parts.map(encodeURIComponent).join("/")
  };
}

function details(role,items) {
  const box=$("#role-detail");
  box.hidden=!role;
  box.replaceChildren();
  if (!role) return;
  box.append(node("h3",role.name),node("p",role.mandate));
  for (const item of items) {
    const article=node("article");
    article.append(badge(item.status),node("p",`${item.product} · ${item.title}`),node("p",item.note));
    if (item.record && !demo) {
      const record=recordLink(item.record);
      const link=node("a",record.title);
      link.href=record.href;
      link.target="_blank";
      link.rel="noopener";
      article.append(link);
    }
    box.append(article);
  }
}

function render() {
  if (!catalog) return;
  setConnection();
  const roster=$("#roster");
  const data=demo ? demoSnapshot : latest;
  const members=catalog.roles;
  const states={};
  const assignments={};
  const meetings=new Map();
  const counts={working:0,queued:0,review:0};
  const capturedFocus=document.activeElement?.dataset.role;
  const rows=new Map(groups.map(name=>[name,[]]));
  for (const [i,role] of members.entries()) {
    const items=[...(data.roles[role.name] || [])].sort((a,b) => rank[a.status]-rank[b.status]);
    assignments[role.name]=items;
    const current=items[0];
    const status=current?.status || "idle";
    states[role.name]={status};
    for (const item of items) {
      if (item.status in counts) counts[item.status]+=1;
      if (item.status==="working") {
        if (!meetings.has(item.record)) meetings.set(item.record,[]);
        const participants=meetings.get(item.record);
        if (!participants.includes(role.name)) participants.push(role.name);
      }
    }
    if (filter==="active" && status!=="working") continue;
    if (filter==="needs-review" && !attention.has(status)) continue;
    const row=node("button","","member");
    row.type="button";
    row.dataset.role=role.name;
    row.setAttribute("aria-pressed",String(selected===role.name));
    const avatar=node("span",role.name.split(" ").map(word=>word[0]).slice(0,2).join(""),"avatar");
    avatar.style.setProperty("--avatar",ROLE_COLORS[i]);
    const text=node("span","","member-info");
    text.append(node("strong",role.name),node("small",current ? `${current.product} · ${current.note}` : role.desk));
    row.append(avatar,text,badge(status));
    row.addEventListener("click",()=>choose(role.name));
    let group=role.group==="Specialist"?"Available specialists":"Available";
    if (status==="working") group="In progress";
    else if (attention.has(status)) group="Needs attention";
    else if (status==="queued") group="Queued";
    rows.get(group).push(row);
  }
  roster.replaceChildren();
  for (const [group,items] of rows) {
    if (!items.length) continue;
    const section=node("section","","role-group");
    section.append(node("h3",group),...items);
    roster.append(section);
  }
  const visible=[...rows.values()].flat();
  $("#roster-count").textContent=filter==="all" ? `${visible.length} roles` : `${visible.length} of ${members.length}`;
  if (!visible.length) roster.append(node("p",filter==="active"?"Nobody is working right now.":"No assignments need attention.","empty"));
  if (capturedFocus) visible.find(row=>row.dataset.role===capturedFocus)?.focus({preventScroll:true});
  for (const [state,total] of Object.entries(counts)) $("#"+state).textContent=total;
  const open=members.find(role=>role.name===selected);
  details(open,assignments[selected] || []);
  const group=[...meetings.values()].sort((a,b)=>b.length-a.length)[0] || [];
  const meeting=group.length>1 && (connected || demo);
  const room=$("#room");
  room.classList.toggle("occupied",meeting);
  room.replaceChildren(node("i"),document.createTextNode(meeting ? `${group.length} in the war room` : "War room available"));
  if (connected || demo) office?.setState(states,meeting ? group : [],selected);
  else office?.setState({},[],selected);
  const history=$("#history");
  history.replaceChildren();
  if (!data.history.length) history.append(node("p","Activity will appear here when an HQ assignment changes.","empty"));
  for (const entry of data.history) {
    const event=node("div","","event");
    const time=node("time",formatTime.format(new Date(entry.updated)));
    time.dateTime=entry.updated;
    const summary=node(!demo && entry.record?"a":"span",`${entry.role} · ${entry.title}`);
    if (summary.tagName==="A") summary.href=recordLink(entry.record).href;
    summary.title=entry.note;
    event.append(badge(entry.status),summary,time);
    history.append(event);
  }
}

async function refresh() {
  const wasConnected=connected;
  try {
    const resp=await fetch("/api/activity",{cache:"no-store",signal:AbortSignal.timeout(4200)});
    if (!resp.ok) throw new Error(`Status ${resp.status}`);
    const payload=await resp.text();
    if (payload!==lastPayload) {
      latest=JSON.parse(payload);
      lastPayload=payload;
      connected=true;
      if (!demo) render();
    } else {
      connected=true;
      if (!wasConnected && !demo) render();
    }
  } catch {
    connected=false;
    if (wasConnected && !demo) render();
    setConnection();
  } finally {
    setTimeout(refresh,1100);
  }
}

(async () => {
  try {
    const response=await fetch("/catalog.json");
    if (!response.ok) throw new Error("The team catalog could not load.");
    catalog=await response.json();
  } catch (error) {
    showMessage(error.message);
    setConnection();
    return;
  }
  try {
    office=buildOffice($("#scene"),catalog.roles,choose);
  } catch (error) {
    console.error(error);
    showMessage("This browser couldn’t load the 3D scene. Live team status is still available.");
  }
  $("#zoom-in").addEventListener("click",()=>office?.zoom(1.19));
  $("#zoom-out").addEventListener("click",()=>office?.zoom(1/1.19));
  const zones=[...document.querySelectorAll("[data-zone]")];
  $("#reset").addEventListener("click",()=>{
    zones.forEach(button=>button.setAttribute("aria-pressed","false"));
    office?.reset();
  });
  for (const button of zones) button.addEventListener("click",()=>{
    zones.forEach(zone=>zone.setAttribute("aria-pressed",String(zone===button)));
    office?.focus(button.dataset.zone);
  });
  const filters=["all","active","needs-review"].map(id=>$("#"+id));
  for (const button of filters) button.addEventListener("click",()=>{
    filter=button.id;
    filters.forEach(item=>item.setAttribute("aria-pressed",String(item===button)));
    render();
  });
  $("#demo").addEventListener("click",()=>{
    demo=!demo;
    if (demo) demoSnapshot=makeDemo();
    $("#demo").setAttribute("aria-pressed",String(demo));
    $("#demo").textContent=demo ? "Exit demo" : "Demo mode";
    render();
  });
  render();
  refresh();
})();
