export function initAdvisor({guide, provider, selected, addSkills}) {
  const storageKey = "evolve-hq-advisor";
  const form = document.querySelector("#advisor-form");
  const input = document.querySelector("#advisor-input");
  const thread = document.querySelector("#advisor-thread");
  const status = document.querySelector("#advisor-status");
  const send = document.querySelector("#advisor-send");
  const reset = document.querySelector("#advisor-reset");
  let busy = false;
  let messages;
  try {
    const stored = JSON.parse(sessionStorage.getItem(storageKey) || "[]");
    messages = Array.isArray(stored) ? stored.filter(message =>
      ["user","assistant"].includes(message?.role) && typeof message?.text === "string").slice(-16) : [];
  } catch {
    messages = [];
  }

  function element(tag, text, classes) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (classes) node.className = classes;
    return node;
  }

  function showStatus(message = "", failure = false) {
    status.textContent = message;
    status.classList.toggle("error", failure);
  }

  function render() {
    const stories = document.createDocumentFragment();
    for (const message of messages) {
      const item = element("article", "", "advisor-message " + message.role);
      item.append(element("strong", message.role === "user" ? "You" : "Evolve"), element("p", message.text));
      const choices = Array.isArray(message.skills) ? message.skills.filter(id => Object.hasOwn(guide, id)) : [];
      if (message.role === "assistant" && choices.length) {
        const actions = element("div", "", "advisor-picks");
        const add = (title, ids) => {
          const button = element("button", title, "secondary");
          button.type = "button";
          button.addEventListener("click", () => {
            addSkills(ids, message.brief);
            button.textContent = "Added to your run";
          });
          actions.append(button);
        };
        for (const id of choices) add("Add " + guide[id].title, [id]);
        if (choices.length > 1) add("Add all suggestions", choices);
        item.append(actions);
      }
      stories.append(item);
    }
    thread.replaceChildren(stories);
    thread.hidden = !messages.length;
    reset.hidden = !messages.length;
    reset.disabled = busy;
    if (!thread.hidden) thread.scrollTop = thread.scrollHeight;
    send.disabled = busy || !input.value.trim();
  }

  function store() {
    try { sessionStorage.setItem(storageKey, JSON.stringify(messages.slice(-16))); }
    catch { /* Chat still works when browser storage is unavailable. */ }
  }

  input.addEventListener("input", () => { send.disabled = busy || !input.value.trim(); });
  reset.addEventListener("click", () => {
    messages = [];
    input.value = "";
    store();
    showStatus();
    render();
    input.focus();
  });
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const text = input.value.trim();
    if (busy || !text) return;
    busy = true;
    messages.push({role:"user", text});
    input.value = "";
    showStatus("Finding the best fit…");
    render();
    try {
      const response = await fetch("/api/advisor", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        signal:AbortSignal.timeout(95000),
        body:JSON.stringify({
          messages:messages.slice(-10).map(({role,text})=>({role,text})),
          provider:provider(),
          selected:selected()
        })
      });
      const answer = await response.json();
      if (!response.ok) throw new Error(answer.error || "Couldn’t get a recommendation. Try again.");
      messages.push({role:"assistant",text:answer.reply,skills:answer.skills,brief:answer.brief});
      messages = messages.slice(-16);
      store();
      showStatus();
    } catch (error) {
      messages.pop();
      input.value = text;
      showStatus(error.name === "TimeoutError" ? "Your AI provider took too long. Try again." : error.message, true);
    } finally {
      busy = false;
      render();
    }
  });
  render();
}
