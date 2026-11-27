import {initAdvisor} from "./advisor.js";

const $=selector=>document.querySelector(selector);
const labels={queued:"Queued",working:"Working",review:"Ready",blocked:"Needs attention",failed:"Stopped",skipped:"Skipped",interrupted:"Interrupted"};
let guide={}, deskBySkill={}, selected=[], visibleLimit=12, runId, sending=false, lastRun="";
let activeTab="workflow", sourceRun="";
const workflows=new Map();
let pending;
const stateMessages={
  queued:"Your selected skills are queued.", working:"The team is preparing your reports.",
  review:"Your reports are ready to review.", blocked:"Finished stages are available. Some stages need attention.", failed:"The run stopped.",
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
  activeTab=tab;
  const skills=tab==="skill";
  $("#skill-panel").hidden=!skills;
  $("#workflow-panel").hidden=skills;
  $("#workflow-tab").setAttribute("aria-pressed",String(!skills));
  $("#skill-tab").setAttribute("aria-pressed",String(skills));
  renderSelection();
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
  const isWorkflow=activeTab==="workflow";
  const count=isWorkflow ? workflows.size : selected.length;
  $("#selection-empty").hidden=Boolean(count);
  const list=$("#selected");
  list.hidden=!count;
  list.replaceChildren();
  for (const action of document.querySelectorAll("[data-workflow-add]")) {
    const current=workflows.get(action.dataset.workflowAdd);
    action.textContent=current?.mode.id===action.dataset.mode ? "Update selection" : "Add to run";
  }
  if (isWorkflow) for (const [id, {workflow,mode,stages}] of workflows) {
    const li=element("li");
    const row=element("div","","selected-line");
    row.append(element("strong",workflow.title),button("×","Remove "+workflow.title,()=>{
      workflows.delete(id);
      renderSelection();
    }));
    li.append(row,element("p",mode.title+" · "+stages.length+" "+(stages.length===1?"stage":"stages"),"muted selected-mode"));
    list.append(li);
  }
  else
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
  $("#selected-count").textContent=`${count} selected`;
  $("#start").disabled=!count || sending;
  $("#jump-to-run").hidden=!count;
  $("#source-run").hidden=!sourceRun || !isWorkflow;
}

function renderWorkflows(catalog) {
  const list=$("#workflow-list");
  for (const workflow of catalog) {
    const card=element("details","","workflow-card");
    const summary=element("summary");
    summary.append(element("strong",workflow.title),element("span",workflow.description));
    const content=element("div","","workflow-options");
    const picker=element("select");
    const label=element("label","What do you want to do?");
    label.append(picker);
    for (const mode of workflow.modes) {
      const option=element("option",mode.title);
      option.value=mode.id;
      picker.append(option);
    }
    const help=element("p","","workflow-help");
    const stages=element("fieldset","","workflow-stages");
    const add=element("button","Add to run","secondary workflow-add");
    add.type="button";
    add.dataset.workflowAdd=workflow.id;
    add.addEventListener("click",()=>{
      const mode=workflow.modes.find(item=>item.id===picker.value);
      const selectedStages=[...stages.querySelectorAll("input:checked")].map(input=>input.value);
      workflows.set(workflow.id,{workflow,mode,stages:selectedStages});
      renderSelection();
      bringSelection();
    });
    function renderMode() {
      const mode=workflow.modes.find(item=>item.id===picker.value);
      const existing=workflows.get(workflow.id);
      add.dataset.mode=mode.id;
      help.textContent=mode.description;
      stages.replaceChildren(element("legend","Choose your stages"));
      for (const stage of mode.steps) {
        const label=element("label");
        const input=element("input");
        input.type="checkbox";
        input.value=stage.id;
        input.checked=existing?.mode.id===mode.id ? existing.stages.includes(stage.id) : true;
        label.append(input,document.createTextNode(stage.title));
        stages.append(label);
      }
      add.disabled=!stages.querySelector("input:checked");
      renderSelection();
    }
    stages.addEventListener("change",()=>{add.disabled=!stages.querySelector("input:checked");});
    picker.addEventListener("change",renderMode);
    content.append(label,help,stages,add);
    card.append(summary,content);
    list.append(card);
    renderMode();
  }
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
  const units=data.workflows?.length ? "stage" : "skill";
  $("#selected-count").textContent=`${data.steps.length} ${units}${data.steps.length===1?"":"s"}`;
  $("#jump-to-run").hidden=true;
  const progress=$("#run-progress");
  progress.hidden=false;
  progress.replaceChildren(element("p",data.error || stateMessages[data.status] || data.status,"status-line"));
  const list=element("ol","","step-results");
  for (const step of data.steps) {
    const li=element("li");
    const job=data.workflows?.find(workflow=>workflow.id===step.workflow);
    const label=element("span",step.title);
    if (job) label.prepend(element("small",job.title,"stage-workflow"));
    li.append(label,element("span",step.phase || labels[step.status] || step.status,"state "+step.status));
    list.append(li);
  }
  progress.append(list);
  const controls=element("div","","progress-actions");
  const office=element("a","See the live office");
  office.href="/";
  if (["review","blocked","failed","interrupted"].includes(data.status)) {
    controls.append(button("Prepare another run","",clearRun,"secondary"));
    if (data.steps.some(step=>step.status==="review" && step.handoff)) {
      controls.append(button("Use reviewed results","",()=>{
        sourceRun=data.id;
        $("#product-name").value=data.product;
        const source=$("#source-run");
        source.replaceChildren(document.createTextNode("Using reviewed results from "+data.product+" "),
          button("Remove","Remove previous run results",()=>{
            sourceRun="";
            renderSelection();
          },"secondary"));
        workflows.clear();
        clearRun();
        showTab("workflow");
      },"secondary"));
    }
  }
  if (data.steps.some(step=>step.report || step.quality)) {
    const reportsLink=element("a","Read reports");
    reportsLink.href="#reports";
    controls.append(reportsLink);
  }
  controls.append(office);progress.append(controls);
  const reports=$("#report-list");
  reports.replaceChildren();
  for (const step of data.steps.filter(step=>step.report || step.quality)) {
    const card=element("article","","report");
    const header=element("header");
    const copy=button("Copy report","",async()=>{
      try {await navigator.clipboard.writeText(step.report);copy.textContent="Copied";}
      catch {copy.textContent="Select report text to copy";}
    },"secondary");
    header.append(element("h3",step.title));
    if (step.report) header.append(copy);
    const content=element("div","","report-body");
    if (step.quality) {
      const review=element("details","","quality-note");
      review.open=step.status!=="review";
      const result=step.status==="review"?"passed":"needs attention";
      const revisions=step.revisions ? ` after ${step.revisions} revision${step.revisions===1?"":"s"}` : "";
      review.append(element("summary","Quality review · "+result+revisions),
        element("p",step.quality));
      if (step.checkResults?.length) {
        const results=element("ul");
        const checkLabels={met:"Met",fix:"Needs revision",missing:"Missing input"};
        for (const check of step.checkResults) {
          const item=element("li");
          item.append(element("strong",checkLabels[check.status]+" · "+check.criterion),
            element("p",check.evidence));
          results.append(item);
        }
        review.append(results);
      }
      content.append(review);
    }
    if (step.report) markdown(content,step.report);
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
  const isWorkflow=activeTab==="workflow";
  if (sending||runId||!(isWorkflow?workflows.size:selected.length)) return;
  error();
  let url=$("#page-url").value.trim();
  if (url&&!url.includes("://")&&!url.includes(" ")) url="https://"+url;
  const brief=$("#brief").value.trim();
  const files=[...$("#images").files];
  if (!url&&!brief&&!files.length&&!(isWorkflow&&sourceRun)) {error("Add a page link, a short brief, or a screenshot first.");$("#page-url").focus();return;}
  if (files.length>3||files.some(file=>file.size>5*1024*1024)) {
    error("Choose up to 3 images, each 5 MB or smaller.");
    return;
  }
  sending=true;
  $("#start").disabled=true;
  const start=$("#start");
  start.firstChild.textContent="Starting your run ";
  try {
    const selection=isWorkflow
      ? {workflows:[...workflows].map(([id,{mode,stages}])=>({workflow:id,mode:mode.id,stages})),sourceRun}
      : {skills:selected};
    const response=await fetch("/api/run",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({...selection,product:$("#product-name").value.trim(),url,brief,
        provider:$("#provider")?.value || "codex",images:await Promise.all(files.map(toBase64))})
    });
    const data=await response.json();
    if (!response.ok) throw new Error(data.error || "The run couldn’t start.");
    history.replaceState(null,"",data.view);
    renderRun(data);follow(data.id);
  } catch (failure) {error(failure.message || "The run couldn’t start. Try again.");}
  finally {sending=false;start.firstChild.textContent="Start run ";renderSelection();}
}
async function initialize() {
  const placeholder=$("#loading-library");
  placeholder.hidden=false;
  try {
    const [catalog,descriptions,workflows]=await Promise.all(["/catalog.json","/skill-guide.json","/api/workflows"].map(async url=>{
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
    renderWorkflows(workflows);
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
      showTab("skill");
      renderSkills();
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
