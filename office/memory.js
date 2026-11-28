const $=selector=>document.querySelector(selector);
const status=$("#memory-status");
const filter=$("#lesson-filter");
const limit=$("#replay-limit");
let state={lessons:[],outcomes:[]};
let guide={};

function node(tag,text,className) {
  const item=document.createElement(tag);
  if (text) item.textContent=text;
  if (className) item.className=className;
  return item;
}
function action(text,callback) {
  const button=node("button",text,"secondary");
  button.type="button";
  button.addEventListener("click",callback);
  return button;
}
async function change(payload) {
  status.textContent="Saving…";
  try {
    const response=await fetch("/api/memory",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify(payload)});
    const result=await response.json();
    if (!response.ok) throw new Error(result.error||"Unable to save.");
    await load();
    status.textContent="Saved.";
  } catch (error) {
    status.textContent=error.message;
  }
}
function renderLessons() {
  const list=$("#lesson-list");
  const query=filter.value.trim().toLowerCase();
  const lessons=state.lessons.filter(lesson=>
    [lesson.skill,guide[lesson.skill]?.title,lesson.brand,lesson.product,lesson.correction]
      .join(" ").toLowerCase().includes(query));
  list.replaceChildren();
  if (!lessons.length) {
    list.append(node("p",query ? "No lessons match this search."
      : "Verified corrections will appear here after HQ revises its work.","muted"));
    return;
  }
  for (const lesson of lessons) {
    const item=node("article",null,"memory-lesson");
    const name=guide[lesson.skill]?.title||lesson.skill;
    const scope=lesson.retired?"Retired":lesson.scope==="tested"?"Tested across products"
      :lesson.scope==="project"?"Current product only":"Awaiting validation";
    item.append(node("h3",lesson.correction),node("p",name+" · "+scope));
    const summary=node("details");
    summary.append(node("summary","Evidence and test status"),
      node("p","When it applies · "+lesson.trigger),
      node("p","How to verify · "+lesson.verification),
      node("p","Before · "+lesson.before),node("p","After · "+lesson.after),
      node("p","Background check · "+lesson.testing+(lesson.result?" · "+lesson.result:"")));
    const origin=node("a",lesson.source.title||"Original run");
    origin.href="/workflows?run="+encodeURIComponent(lesson.source.run);
    summary.append(origin);
    item.append(summary);
    const controls=node("div",null,"progress-actions");
    controls.append(action(lesson.retired?"Restore":"Retire",()=>change({id:lesson.id,retired:!lesson.retired})));
    if (!lesson.retired) {
      controls.append(action("Edit correction",()=>{
        const label=node("label","Updated correction");
        const input=node("textarea");
        input.maxLength=350;
        input.value=lesson.correction;
        label.append(input);
        controls.replaceChildren(label,action("Save edit",()=>change({id:lesson.id,correction:input.value})),
          action("Cancel",renderLessons));
        input.focus();
      }));
    }
    item.append(controls);
    list.append(item);
  }
}
function renderCounts() {
  const group=$("#memory-counts");
  group.replaceChildren();
  if (!state.outcomes.length) {
    group.append(node("p","First-draft results will appear once a run is reviewed.","muted"));
    return;
  }
  for (const record of state.outcomes) {
    const row=node("p",null,"memory-metric");
    row.append(node("strong",guide[record.skill]?.title||record.skill),
      node("span",record.firstPass+"/"+record.stages+" passed on the first draft"),
      node("span",record.repeats+" repeat findings across "+record.recalled+" lesson recalls"));
    group.append(row);
  }
}
async function load() {
  const response=await fetch("/api/memory");
  if (!response.ok) throw new Error("Couldn’t open local learning memory.");
  state=await response.json();
  limit.value=String(state.dailyReplays);
  $("#preference-text").value=state.preference||"";
  renderLessons();
  renderCounts();
}
$("#memory-preference").addEventListener("submit",event=>{
  event.preventDefault();
  change({preference:$("#preference-text").value});
});
filter.addEventListener("input",renderLessons);
limit.addEventListener("change",()=>change({dailyReplays:Number(limit.value)}));
async function init() {
  try {
    const response=await fetch("/skill-guide.json");
    if (response.ok) guide=await response.json();
    await load();
  } catch (error) {
    status.textContent=error.message;
  }
}
init();
