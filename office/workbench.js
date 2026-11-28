import {initAdvisor} from "./advisor.js";

const $=selector=>document.querySelector(selector);
const labels={queued:"Queued",working:"Working",review:"Ready",blocked:"Needs attention",failed:"Stopped",skipped:"Skipped",interrupted:"Interrupted"};
let guide={}, deskBySkill={}, selected=[], visibleLimit=12, runId, sending=false, lastRun="";
let activeTab="workflow", sourceRun="", workspace, workspaceMode, skillPage="";
let workflowCatalog=[];
const pageQuery=new URLSearchParams(location.search);
const directions={
  "market-research":["What do you sell, and what would you like to find out?","Example: I sell adjustable dog harnesses. I want to find out why people hesitate to order."],
  "copywriting":["Who are you writing for, and what should they do next?","Example: Write the opening for first-time visitors. I want them to check which size fits."],
  "native-ads":["What should the ad make someone understand or do?","Example: Write a short Facebook story for people who are unsure how to measure their dog."],
  "static-ads":["What should someone understand from the picture?","Example: Show where to measure a dog. I can supply a product photo."],
  "ad-review":["What did you expect this ad to do, and what happened?","Example: The ad gets clicks but few sales. Help me find where shoppers lose interest."],
  "store-cro":["Which page should we look at, and where might shoppers get stuck?","Example: On phones, people ask what comes in the bundle. Review the first screen."],
};
const supplementarySkills={
  "market-research":["evolve-positioning","evolve-competitor-creative"],
  "copywriting":["humanizer","offers"],
  "native-ads":["cold-traffic-ad-craft","write-video-ad-scripts"],
  "static-ads":["build-static-ads-in-figma","adapt-reference-ad","metaphor-ads"],
  "ad-review":["evolve-test-design","evolve-roadmap"],
  "store-cro":["ab-testing","analytics"],
};
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
function copyButton(label,content,fallback) {
  const item=button(label,"",async()=>{
    try {await navigator.clipboard.writeText(content);item.textContent="Copied";}
    catch {item.textContent=fallback;}
  },"secondary");
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
  $("#static-libraries").hidden=skills;
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
  const home=activeTab==="workflow"&&!workspace&&!$("#batch-picker").open&&!workflows.size&&!sourceRun;
  $("#workbench").classList.toggle("directory-open",home);
  $(".composer").hidden=home;
  const isWorkflow=activeTab==="workflow";
  const count=isWorkflow ? workflows.size : selected.length;
  const materials=isWorkflow
    ? [...workflows.values()].map(({mode})=>[mode.title,mode.inputs])
    : selected.map(id=>[guide[id].title,guide[id].inputs]);
  const guidance=$("#input-guidance");
  const stepCount=workspace ? workflows.get(workspace.id)?.stages.length||0 : 0;
  if (materials.length>1) {
    const list=element("ul");
    for (const [title,inputs] of materials) {
      const row=element("li");
      row.append(element("strong",title+" — "),document.createTextNode(inputs||"Add relevant context or screenshots."));
      list.append(row);
    }
    guidance.replaceChildren(list);
  } else {
    guidance.textContent=materials.length
      ? materials[0][1] || "Add a page link, a brief, or relevant screenshots."
      : "Select a workflow or skill to see what to bring.";
  }
  $("#selection-empty").hidden=Boolean(count);
  const list=$("#selected");
  list.hidden=!count;
  list.replaceChildren();
  for (const action of document.querySelectorAll("[data-workflow-add]")) {
    const current=workflows.get(action.dataset.workflowAdd);
    action.textContent=current?.mode.id===action.dataset.mode ? "Update selection" : "Add to run";
  }
  if (isWorkflow&&!workspace) for (const [id, {workflow,mode,stages}] of workflows) {
    const li=element("li");
    const row=element("div","","selected-line");
    row.append(element("strong",workflow.title),button("×","Remove "+workflow.title,()=>{
      workflows.delete(id);
      renderSelection();
    }));
    li.append(row,element("p",mode.title+" · "+stages.length+" "+(stages.length===1?"stage":"stages"),"muted selected-mode"));
    list.append(li);
  }
  else if (!isWorkflow)
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
  if (workspace&&!stepCount) guidance.textContent="Select at least one step in the plan to start.";
  $("#selected-count").textContent=workspace
    ? `${stepCount} ${stepCount===1?"step":"steps"} selected` : `${count} selected`;
  if (workspace) $("#selection-empty").hidden=true;
  $("#start").disabled=!count||sending||Boolean(workspace&&!stepCount);
  $("#jump-to-run").hidden=!count;
  $("#jump-to-run").textContent=workspace?"Go to run setup":"Review your selections";
  $("#source-run").hidden=!sourceRun || !isWorkflow;
}

function workspaceURL(workflow,mode) {
  const query=new URLSearchParams({workflow});
  if (mode) query.set("mode",mode);
  return "/workflows?"+query;
}

function newTabLink(text,href,style="") {
  const link=element("a",text,style);
  link.href=href;
  link.target="_blank";
  link.rel="noopener";
  return link;
}

function renderDirectory(catalog) {
  const list=$("#workflow-directory");
  for (const workflow of catalog) {
    const link=newTabLink("",workspaceURL(workflow.id),"directory-card");
    link.setAttribute("aria-label",workflow.title+" (opens in a new tab)");
    const heading=element("div","","directory-card-head");
    const arrow=element("span","↗");
    arrow.setAttribute("aria-hidden","true");
    heading.append(element("h2",workflow.title),arrow);
    link.append(heading,element("p",workflow.description));
    list.append(link);
  }
}

function restoreWorkspace() {
  $("#pick-intro").hidden=Boolean(workspace);
  $("#guided-intro").hidden=!workspace;
  $("#guided-setup").hidden=!workspace;
  $("#workflow-panel").hidden=Boolean(workspace)||activeTab==="skill";
  $("#library-switch").hidden=Boolean(workspace);
  $("#static-libraries").hidden=workspace ? workspace.id!=="static-ads" : activeTab==="skill";
  $("#input-heading").textContent=workspace?"What should the team know?":"What should we use?";
  const [question,example]=directions[workspace?.id]||[
    "What would you like to improve?",
    "Example: Review the first screen on mobile and tell me which photos to replace."
  ];
  $("#brief-caption").textContent=question;
  $("#brief").placeholder=example;
  document.title=workspace?`${workspace.title} · Evolve HQ`:"Workflows & skills · Evolve HQ";
}

function openWorkspace(workflow,requestedMode) {
  workspace=workflow;
  $("#guided-title").textContent=workflow.title;
  $("#guided-description").textContent=workflow.description;
  const nav=$("#workflow-navigation");
  const back=element("a","All workflows","workflow-back");
  back.href="/workflows";
  nav.replaceChildren(back);
  const tabs=element("div","","workflow-tabs");
  for (const entry of workflowCatalog) {
    const link=element("a",entry.title);
    link.href=workspaceURL(entry.id);
    if (entry.id===workflow.id) link.setAttribute("aria-current","page");
    tabs.append(link);
  }
  nav.append(tabs);

  const setup=$("#guided-setup");
  const goals=element("fieldset","","guided-goals");
  const plan=element("section","","guided-plan");
  goals.append(element("legend","What do you want to do?"));
  setup.replaceChildren(goals,plan);
  const modes=element("div","","guided-modes");
  goals.append(modes);
  for (const mode of workflow.modes) {
    const label=element("label","","guided-mode");
    const input=element("input");
    input.type="radio";
    input.name="guided-mode";
    input.value=mode.id;
    label.append(input,element("span",mode.title,"mode-name"));
    modes.append(label);
  }

  function chooseMode(modeId) {
    const mode=workflow.modes.find(entry=>entry.id===modeId)||workflow.modes[0];
    workspaceMode=mode.id;
    modes.querySelectorAll("input").forEach(input=>{input.checked=input.value===mode.id;});
    workflows.set(workflow.id,{workflow,mode,stages:mode.steps.map(step=>step.id)});
    const overview=element("p",mode.description,"plan-description");
    const steps=element("fieldset","","guided-steps workflow-stages");
    steps.append(element("legend","What the team will do"));
    for (const step of mode.steps) {
      const row=element("div","","guided-step");
      const label=element("label");
      const input=element("input");
      input.type="checkbox";
      input.value=step.id;
      input.checked=true;
      const skill=guide[step.skill];
      label.append(input,element("span",step.title,"step-name"));
      row.append(label);
      if (skill) {
        const link=newTabLink(skill.title,"/workflows?skill="+encodeURIComponent(step.skill),"step-skill");
        link.setAttribute("aria-label","Run on its own: "+skill.title+" (opens in a new tab)");
        row.append(link);
      }
      steps.append(row);
    }
    steps.addEventListener("change",()=>{
      workflows.get(workflow.id).stages=[...steps.querySelectorAll("input:checked")].map(input=>input.value);
      renderSelection();
    });
    const otherSkills=element("details","","related-skills");
    otherSkills.append(element("summary","Skills available for this workflow"));
    const skills=element("ul");
    const usedSkills=new Set(mode.steps.map(step=>step.skill));
    const allSkills=new Set(workflow.modes.flatMap(entry=>entry.steps.map(step=>step.skill)));
    for (const id of supplementarySkills[workflow.id]||[]) allSkills.add(id);
    for (const id of allSkills) {
      const skill=guide[id];
      if (!skill) continue;
      const row=element("li");
      row.append(newTabLink(skill.title,"/workflows?skill="+encodeURIComponent(id)),element("p",skill.description));
      if (usedSkills.has(id)) row.classList.add("used-skill");
      skills.append(row);
    }
    otherSkills.append(skills);
    plan.replaceChildren(overview,steps,otherSkills);
    if (!new URLSearchParams(location.search).has("run")&&!runId) history.replaceState(null,"",workspaceURL(workflow.id,mode.id));
    renderSelection();
  }
  modes.addEventListener("change",event=>chooseMode(event.target.value));
  restoreWorkspace();
  chooseMode(requestedMode);
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
function skillSearchWords(text) {
  return text.toLowerCase().match(/[\p{L}\p{N}]+/gu)||[];
}
function renderSkills() {
  const smallWords=new Set(["a","an","the","for","my","to","me","and","on","with","of"]);
  const search=skillSearchWords($("#search").value).filter(word=>!smallWords.has(word));
  const phrase=search.join(" ");
  const desk=$("#desk").value;
  const result=[];
  for (const [id,info] of Object.entries(guide)) {
    if (desk&&deskBySkill[id]!==desk) continue;
    const names=[id,info.title,...(info.search_aliases||[])];
    const haystack=skillSearchWords([...names,info.description,info.inputs,info.output].join(" ")).join(" ");
    if (!search.every(word=>haystack.includes(word))) continue;
    const direct=phrase&&names.some(name=>skillSearchWords(name).filter(word=>!smallWords.has(word)).join(" ")===phrase);
    result.push({id,direct:Boolean(direct)});
  }
  result.sort((a,b)=>Number(b.direct)-Number(a.direct));
  const list=$("#skill-list");
  list.replaceChildren(...result.slice(0,visibleLimit).map(({id})=>skillRow(id)));
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
  let list, code, block, quote, imagePrompt;
  const lines=markdownText.split("\n");
  const cells=line=>line.trim().replace(/^\||\|$/g,"").split("|").map(cell=>cell.trim());
  for (let index=0;index<lines.length;index++) {
    const raw=lines[index];
    const line=raw.trim();
    if (line.startsWith("```")) {
      if (code) {
        const content=code.textContent.slice(0,-1);
        if (imagePrompt&&content.trim()) {
          body.append(copyButton("Copy image prompt",content,"Select the prompt to copy"));
        }
        code=null;
        continue;
      }
      imagePrompt=line==="```image-prompt";
      code=element("pre");
      if(line==="```static-layout") {
        const layout=element("details");
        layout.append(element("summary","Layout details"),code);
        body.append(layout);
      } else body.append(code);
      list=null;block=null;continue;
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
function imagePreview(run,step) {
  const panel=element("div","","static-preview");
  const status=element("p","","muted");
  status.setAttribute("role","status");
  const preview=button("Preview image","",async()=>{
    preview.disabled=true;
    status.textContent="Rendering locally…";
    try {
      const response=await fetch("/api/static-preview",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({run,step})
      });
      const result=await response.json();
      if (!response.ok) throw new Error(result.error||"The preview couldn’t render.");
      const image=element("img");
      image.src="data:image/png;base64,"+result.png;
      image.alt="Preview of the reviewed image ad layout";
      const links=element("div","","progress-actions");
      for (const [format,type,label] of [["png","png","Download PNG"],["svg","svg+xml","Download editable SVG"]]) {
        const link=element("a",label);
        link.href="data:image/"+type+";base64,"+result[format];
        link.download="image-ad."+format;
        links.append(link);
      }
      status.textContent="Preview ready. Check the image and wording before you use it.";
      panel.append(image,links);
      preview.remove();
    } catch (error) {
      status.textContent=error.message||"The preview couldn’t render.";
      preview.disabled=false;
    }
  },"secondary");
  panel.append(preview,status);
  return panel;
}
function clearRun() {
  clearTimeout(pending);
  runId=undefined;lastRun="";
  history.replaceState(null,"",workspace ? workspaceURL(workspace.id,workspaceMode) : skillPage ? "/workflows?skill="+encodeURIComponent(skillPage) : "/workflows");
  $("#run-progress").hidden=true;
  $("#reports").hidden=true;
  $("#workbench").classList.remove("run-open");
  restoreWorkspace();
  $("#result-intro").hidden=true;
  $("#run-form").hidden=false;
  renderSelection();
}
function reuseResults(data, approved) {
  sourceRun=data.id;
  const source=$("#source-run");
  source.replaceChildren(element("legend","Reviewed results to reuse"));
  for (const step of approved) {
    const label=element("label");
    const input=element("input");
    input.type="checkbox";
    input.name="source-step";
    input.value=step.id;
    input.checked=true;
    label.append(input,document.createTextNode(step.title));
    source.append(label);
  }
  if (data.imageCount) {
    const label=element("label","","source-images");
    const input=element("input");
    input.type="checkbox";
    input.id="source-images";
    const count=data.imageCount;
    label.append(input,document.createTextNode(`Include ${count} ${count===1?'image':'images'} from the previous run`));
    source.append(label);
  }
  source.append(button("Remove previous run","",()=>{
    sourceRun="";
    error();
    renderSelection();
  },"secondary"));
  $("#product-name").value=data.product;
  for (const id of ["#page-url","#brief","#images"]) $(id).value="";
  updateImageNames();
  error();
  workflows.clear();
  workspace=undefined;
  skillPage="";
  $("#batch-picker").open=true;
  clearRun();
  showTab("workflow");
  source.querySelector("input").focus();
}
function renderRun(data) {
  runId=data.id;
  $("#workbench").classList.add("run-open");
  $(".composer").hidden=false;
  $("#workbench").classList.remove("directory-open");
  $("#pick-intro").hidden=true;
  $("#guided-intro").hidden=true;
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
    const approved=data.steps.filter(step=>step.status==="review" && step.handoff && step.artifact);
    if (approved.length) {
      controls.append(button("Use reviewed results","",()=>reuseResults(data,approved),"secondary"));
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
    const copy=copyButton("Copy report",step.report,"Select report text to copy");
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
      if (step.judgment) {
        const note=step.judgment;
        review.append(element("strong","Why this approach"),element("p",note.choice),
          element("p",note.basis),element("strong","What would change it"),element("p",note.reconsiderIf));
      }
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
      if (step.references?.length) {
        const sources=element("ul");
        for (const source of step.references) {
          const file=source.file.split(/[\\/]/).slice(-2).join("/");
          const location=source.startLine ? file+" line "+source.startLine : file;
          sources.append(element("li",location+" · "+source.decision));
        }
        review.append(element("strong","Local references checked"),sources);
      }
      content.append(review);
    }
    if (step.status==="review"&&!data.workflows?.length&&step.skill==="build-static-ads-in-figma"
        &&step.report?.includes("```static-layout")) {
      content.append(imagePreview(data.id,step.id));
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
  if (sending||runId||!(isWorkflow?workflows.size:selected.length)||
      (workspace&&!workflows.get(workspace.id)?.stages.length)) return;
  error();
  let url=$("#page-url").value.trim();
  if (url&&!url.includes("://")&&!url.includes(" ")) url="https://"+url;
  const brief=$("#brief").value.trim();
  const files=[...$("#images").files];
  const sourceSteps=[...document.querySelectorAll('#source-run input[name="source-step"]:checked')].map(input=>input.value);
  const handoff=isWorkflow&&sourceRun ? {sourceRun,sourceSteps,sourceImages:$("#source-images")?.checked ?? false} : {};
  if (handoff.sourceRun&&!sourceSteps.length) {error("Select a reviewed result or remove the previous run.");return;}
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
      ? {workflows:[...workflows].map(([id,{mode,stages}])=>({workflow:id,mode:mode.id,stages})),...handoff}
      : {skills:selected};
    const response=await fetch("/api/run",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({...selection,product:$("#product-name").value.trim(),url,brief,
        provider:$("#provider")?.value || "codex",images:await Promise.all(files.map(toBase64))})
    });
    const data=await response.json();
    if (!response.ok) throw new Error(data.error || "The run couldn’t start.");
    const resultURL=new URL(data.view,location.origin);
    if (workspace) {
      resultURL.searchParams.set("workflow",workspace.id);
      resultURL.searchParams.set("mode",workspaceMode);
    } else if (skillPage) resultURL.searchParams.set("skill",skillPage);
    history.replaceState(null,"",resultURL);
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
    workflowCatalog=workflows;
    renderDirectory(workflows);
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
  const jump=$("#jump-to-run");
  jump.addEventListener("click",bringSelection);
  const observeForm=new IntersectionObserver(([entry])=>{
    jump.classList.toggle("form-in-view",entry.isIntersecting);
  });
  observeForm.observe($("#run-title"));
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
  $("#batch-picker").addEventListener("toggle",renderSelection);
  const workflow=workflowCatalog.find(entry=>entry.id===pageQuery.get("workflow"));
  const requestedSkill=pageQuery.get("skill");
  if (workflow) openWorkspace(workflow,pageQuery.get("mode"));
  else if (requestedSkill&&Object.hasOwn(guide,requestedSkill)) {
    skillPage=requestedSkill;
    selected=[skillPage];
    $("#search").value=skillPage;
    showTab("skill");
    renderSkills();
  }
  const id=pageQuery.get("run");
  if (id) {
    runId=id;
    $("#run-form").hidden=true;
    $("#run-progress").hidden=false;
    $("#run-progress").append(element("p","Loading this run…","status-line"));
    follow(id);
  }
}
initialize();
