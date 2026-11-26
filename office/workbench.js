import {initAdvisor} from "./advisor.js";

const $=selector=>document.querySelector(selector);
const presets={
  store:["store-content-cro-review"],
  angles:["evolve-angles","evolve-test-design"],
  ad:["analyze-ads"],
  page:["write-product-page-copy"]
};
const labels={queued:"Queued",working:"Working",review:"Ready",failed:"Stopped",skipped:"Skipped",interrupted:"Interrupted"};
let guide={}, deskBySkill={}, selected=[], visibleLimit=12, runId, sending=false, lastRun="";
let pending;
const stateMessages={
  queued:"Your selected skills are queued.", working:"The team is preparing your reports.",
  review:"Your reports are ready to review.", failed:"The run stopped.",
  interrupted:"The Mac stopped while this run was in progress."
};

function element(tag,text,cls) {
  const item=document.createElement(tag);
  if (text) item.textContent=text;
  if (cls) item.className=cls;
  return item;
}
function button(text,label,action,cls="") {
  const item=element("button",text,cls);
  item.type="button";
  if (label) item.setAttribute("aria-label",label);
  item.addEventListener("click",action);
  return item;
}
function error(message="") {
  $("#run-error").textContent=message;
  $("#run-error").hidden=!message;
}
function showTab(tab) {
  const skills=tab==="skill";
  $("#skill-panel").hidden=!skills;
  $("#workflow-panel").hidden=skills;
  $("#workflow-tab").setAttribute("aria-pressed",String(!skills));
  $("#skill-tab").setAttribute("aria-pressed",String(skills));
}
function bringSelection() {
  $("#run-title").closest(".composer").scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth",block:"start"});
}

function renderSelection() {
  for (const add of document.querySelectorAll(".skill-add")) {
    const state=selected.includes(add.dataset.skill);
    add.textContent=state?"Added":"Add";
    add.setAttribute("aria-pressed",String(state));
  }
  if (runId) return;
  $("#selection-empty").hidden=Boolean(selected.length);
  const list=$("#selected");
  list.hidden=!selected.length;
  list.replaceChildren();
  selected.forEach((id,index)=>{
    const info=guide[id];
    const li=element("li");
    const row=element("div","","selected-line");
    row.append(element("strong",info.title));
    if (index>0) row.append(button("↑","Move up: "+info.title,()=>{
      [selected[index-1],selected[index]]=[selected[index],selected[index-1]];
      renderSelection();
    }));
    row.append(button("×","Remove: "+info.title,()=>{
      selected=selected.filter(key=>id!==key);
      renderSelection();
    }));
    li.append(row);
    list.append(li);
  });
  $("#selected-count").textContent=`${selected.length} selected`;
  $("#start").disabled=!selected.length || sending;
  $("#jump-to-run").hidden=!selected.length || Boolean(runId);
}

function skillRow(id) {
  const info=guide[id];
  const row=element("article","","skill-row");
  const copy=element("div");
  copy.append(element("h3",info.title),element("p",info.description));
  const add=button("Add",`Select or remove ${info.title}`,()=>{
    selected=selected.includes(id)?selected.filter(item=>item!==id):[...selected,id];
    renderSelection();
  },"skill-add");
  add.dataset.skill=id;
  const details=element("details");
  const exact=element("dl");
  const facts=[["You’ll need",info.inputs],["You’ll get",info.output],["Team",deskBySkill[id]],["Skill name",id]];
  if (info.kind==="workflow") facts.splice(2,0,["Format","A complete procedure with its own internal steps."]);
  for (const [key,value] of facts) exact.append(element("dt",key),element("dd",value));
  details.append(element("summary","What it needs and what you get"),exact);
  row.append(copy,add,details);
  return row;
}
function renderSkills() {
  const search=$("#search").value.toLowerCase().trim().split(/\s+/);
  const desk=$("#desk").value;
  const result=Object.entries(guide).filter(([id,info])=>{
    const text=[id,info.title,info.description,info.inputs,info.output].join(" ").toLowerCase();
    return (!desk||deskBySkill[id]===desk) && search.every(term=>text.includes(term));
  });
  const list=$("#skill-list");
  list.replaceChildren(...result.slice(0,visibleLimit).map(([id])=>skillRow(id)));
  if (result.length>visibleLimit) list.append(button("Show more skills","",()=>{
    visibleLimit+=12;
    renderSkills();
  },"secondary more-skills"));
  $("#skill-results").textContent=result.length?`${result.length} skills`:"No skills match. Try a different search or team.";
  renderSelection();
}

const toBase64=file=>new Promise((resolve,reject)=>{
  const reader=new FileReader();
  reader.onload=()=>resolve(String(reader.result).split(",")[1]);
  reader.onerror=()=>reject(new Error("That image couldn’t be read."));
  reader.readAsDataURL(file);
});

function updateImageNames() {
  const files=[...$("#images").files];
  $("#image-names").textContent=files.map(file=>file.name).join(" · ");
}
function inline(text, target) {
  // Treat model output as text. Turn only ordinary links and emphasis into markup.
  const parts=text.split(/(\*\*[^*]+\*\*|\[[^\]\n]+\]\(https?:\/\/[^\s)]+\))/g);
  for (const part of parts) {
    const match=part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
    if (match) {
      const a=element("a",match[1]);
      a.href=match[2];a.target="_blank";a.rel="noopener noreferrer";
      target.append(a);
    } else if (part.startsWith("**") && part.endsWith("**") && part.length>4) {
      target.append(element("strong",part.slice(2,-2)));
    } else target.append(document.createTextNode(part));
  }
}
function markdown(body, markdownText) {
  let list, code, block, quote;
  const lines=markdownText.split("\n");
  const cells=line=>line.trim().replace(/^\||\|$/g,"").split("|").map(cell=>cell.trim());
  for (let index=0;index<lines.length;index++) {
    const raw=lines[index];
    const line=raw.trim();
    if (line.startsWith("```")) {
      if (code) {code=null;continue;}
      code=element("pre");
      body.append(code);list=null;block=null;continue;
    }
    if (code) {code.append(document.createTextNode(raw+"\n"));continue;}
    if (!line) {list=null;block=null;quote=null;continue;}
    if (line.startsWith("> ")) {
      if (!quote) {quote=element("blockquote");body.append(quote);}
      else quote.append(document.createElement("br"));
      inline(line.slice(2),quote);list=null;block=null;
      continue;
    }
    quote=null;
    if (line.includes("|") && lines[index+1]?.includes("|") &&
        cells(lines[index+1]).every(cell=>/^:?-{3,}:?$/.test(cell))) {
      const wrapper=element("div","","table-wrap");
      const table=element("table");
      const head=table.createTHead().insertRow();
      for (const cell of cells(line)) {
        const column=element("th");
        column.scope="col";
        inline(cell,column);
        head.append(column);
      }
      const rows=table.createTBody();
      index++;
      while (lines[index+1]?.trim().startsWith("|")) {
        const row=rows.insertRow();
        for (const cell of cells(lines[++index])) inline(cell,row.insertCell());
      }
      wrapper.append(table);body.append(wrapper);list=null;block=null;
      continue;
    }
    const heading=line.match(/^#{1,6}\s+(.+)$/);
    const bullet=line.match(/^(?:[-*]|(\d+)\.)\s+(.+)$/);
    if (heading) {
      const title=element("h4");
      inline(heading[1],title);body.append(title);list=null;block=null;
    } else if (bullet) {
      const tag=bullet[1]?"OL":"UL";
      if (!list||list.tagName!==tag) {list=element(tag.toLowerCase());body.append(list);}
      const li=element("li");inline(bullet[2],li);list.append(li);block=null;
    } else {
      list=null;
      if (!block) {block=element("p");body.append(block);}
      else block.append(document.createElement("br"));
      inline(line,block);
    }
  }
}
function clearRun() {
  clearTimeout(pending);
  runId=undefined;lastRun="";
  history.replaceState(null,"","/workflows");
  $("#run-progress").hidden=true;
  $("#reports").hidden=true;
  $("#workbench").classList.remove("run-open");
  $("#pick-intro").hidden=false;
  $("#result-intro").hidden=true;
  $("#run-form").hidden=false;
  renderSelection();
}
function renderRun(data) {
  runId=data.id;
  $("#workbench").classList.add("run-open");
  $("#pick-intro").hidden=true;
  $("#result-intro").hidden=false;
  $("#run-form").hidden=true;
  $("#selection-empty").hidden=true;
  $("#selected").hidden=true;
  $("#selected-count").textContent=`${data.steps.length} ${data.steps.length===1?"skill":"skills"}`;
  $("#jump-to-run").hidden=true;
  const progress=$("#run-progress");
  progress.hidden=false;
  progress.replaceChildren(element("p",data.error || stateMessages[data.status] || data.status,"status-line"));
  const list=element("ol","","step-results");
  for (const step of data.steps) {
    const li=element("li");
    li.append(element("span",step.title),element("span",labels[step.status] || step.status,"state "+step.status));
    list.append(li);
  }
  progress.append(list);
  const controls=element("div","","progress-actions");
  const office=element("a","See the live office");
  office.href="/";
  if (["review","failed","interrupted"].includes(data.status)) {
    controls.append(button("Prepare another run","",clearRun,"secondary"));
  }
  if (data.steps.some(step=>step.report)) {
    const reportsLink=element("a","Read reports");
    reportsLink.href="#reports";
    controls.append(reportsLink);
  }
  controls.append(office);progress.append(controls);
  const reports=$("#report-list");
  reports.replaceChildren();
  for (const step of data.steps.filter(step=>step.report)) {
    const card=element("article","","report");
    const header=element("header");
    const copy=button("Copy report","",async()=>{
      try {await navigator.clipboard.writeText(step.report);copy.textContent="Copied";}
      catch {copy.textContent="Select report text to copy";}
    },"secondary");
    header.append(element("h3",step.title),copy);
    const content=element("div","","report-body");
    markdown(content,step.report);
    card.append(header,content);reports.append(card);
  }
  if (!reports.childElementCount) {
    const active=["queued","working"].includes(data.status);
    reports.append(element("p",active?"The first report will appear here when it’s ready.":"This run ended before a report was ready.","muted report-empty"));
  }
  $("#reports").hidden=false;
}
function follow(id) {
  clearTimeout(pending);
  async function check() {
    if (runId!==id) return;
    try {
      const response=await fetch("/api/run?id="+encodeURIComponent(id),{signal:AbortSignal.timeout(5000)});
      const data=await response.json();
      if (response.status===404) {clearRun();error("This run could not be found.");return;}
      if (!response.ok) throw new Error();
      if (runId!==id) return;
      const key=JSON.stringify(data);
      if (key!==lastRun) {lastRun=key;renderRun(data);}
      if (!["queued","working"].includes(data.status)) return;
    } catch {
      const status=$("#run-progress .status-line");
      if (status) status.textContent="Reconnecting to Evolve HQ…";
      lastRun="";
    }
    if (runId===id) pending=setTimeout(check,1150);
  }
  check();
}
async function submit(event) {
  event.preventDefault();
  if (sending||runId||!selected.length) return;
  error();
  let url=$("#page-url").value.trim();
  if (url&&!url.includes("://")&&!url.includes(" ")) url="https://"+url;
  const brief=$("#brief").value.trim();
  const files=[...$("#images").files];
  if (!url&&!brief&&!files.length) {error("Add a page link, a short brief, or a screenshot first.");$("#page-url").focus();return;}
  if (files.length>3||files.some(file=>file.size>5*1024*1024)) {
    error("Choose up to 3 images, each 5 MB or smaller.");
    return;
  }
  sending=true;
  $("#start").disabled=true;
  const start=$("#start");
  start.firstChild.textContent="Starting your run ";
  try {
    const response=await fetch("/api/run",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({skills:selected,url,brief,provider:$("#provider").value || "codex",images:await Promise.all(files.map(toBase64))})
    });
    const data=await response.json();
    if (!response.ok) throw new Error(data.error || "The run couldn’t start.");
    history.replaceState(null,"",data.view);
    renderRun(data);follow(data.id);
  } catch (failure) {error(failure.message || "The run couldn’t start. Try again.");}
  finally {sending=false;start.firstChild.textContent="Run selected skills ";renderSelection();}
}
async function initialize() {
  const placeholder=$("#loading-library");
  placeholder.hidden=false;
  try {
    const [catalog,descriptions]=await Promise.all(["/catalog.json","/skill-guide.json"].map(async url=>{
      const response=await fetch(url);
      if (!response.ok) throw new Error();
      return response.json();
    }));
    guide=descriptions;
    for (const desk of [...catalog.desks,{name:"Shared workflows",skills:catalog.sharedSkills}]) {
      const option=element("option",desk.name);
      option.value=desk.name;
      $("#desk").append(option);
      for (const id of desk.skills) deskBySkill[id]=desk.name;
    }
    $("#skill-count").textContent=Object.keys(guide).length;
    placeholder.hidden=true;
  } catch {
    placeholder.textContent="The library couldn’t load. Reopen Evolve HQ or refresh this page.";
    return;
  }
  const provider=$("#provider");
  const providerStatus=$("#provider-status");
  let providers=[{id:"codex",label:"Codex",installed:false}];
  try {
    const response=await fetch("/api/providers");
    if (response.ok) providers=await response.json();
  } catch { /* The setup guide remains available if the status check fails. */ }
  for (const entry of providers) {
    const option=element("option",entry.label);
    option.value=entry.id;
    provider.append(option);
  }
  try {
    const stored=localStorage.getItem("evolve-hq-provider");
    if (providers.some(entry=>entry.id===stored)) provider.value=stored;
    else provider.value=providers.find(entry=>entry.installed)?.id || providers[0].id;
  } catch { /* Browser storage is optional. */ }
  function showProvider() {
    const entry=providers.find(item=>item.id===provider.value);
    providerStatus.textContent=entry?.installed?"CLI found · uses your account":"Setup required";
  }
  provider.addEventListener("change",()=>{
    try {localStorage.setItem("evolve-hq-provider",provider.value);} catch { /* Browser storage is optional. */ }
    showProvider();
  });
  showProvider();
  $("#workflow-tab").addEventListener("click",()=>showTab("workflow"));
  $("#skill-tab").addEventListener("click",()=>{showTab("skill");renderSkills();});
  for (const item of document.querySelectorAll("[data-preset]")) item.addEventListener("click",()=>{
    selected=[...presets[item.dataset.preset]];
    if (!runId) renderSelection();
    bringSelection();
  });
  for (const input of [$("#search"),$("#desk")]) input.addEventListener("input",()=>{
    visibleLimit=12;renderSkills();
  });
  $("#images").addEventListener("change",updateImageNames);
  $("#jump-to-run").addEventListener("click",bringSelection);
  $("#run-form").addEventListener("submit",submit);
  initAdvisor({
    guide,
    provider:()=>provider.value || "codex",
    selected:()=>selected,
    addSkills:(ids,brief)=>{
      selected=[...new Set([...selected,...ids])];
      if (brief&&!$("#brief").value.trim()) $("#brief").value=brief;
      renderSelection();
      if (!runId) bringSelection();
    }
  });
  const id=new URLSearchParams(location.search).get("run");
  if (id) {
    runId=id;
    $("#run-form").hidden=true;
    $("#run-progress").hidden=false;
    $("#run-progress").append(element("p","Loading this run…","status-line"));
    follow(id);
  }
}
initialize();
