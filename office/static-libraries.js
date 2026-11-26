const storageKey = "evolve-hq-static-libraries";
const list = document.querySelector("#static-library-list");
const form = document.querySelector("#static-library-form");
const status = document.querySelector("#static-library-status");
const empty = document.querySelector("#static-library-empty");
let configured = [];
let saved = [];

function normalized(item) {
  if (!item || typeof item.name !== "string" || typeof item.url !== "string") return null;
  try {
    const url = new URL(item.url);
    if (!["https:", "http:"].includes(url.protocol) || url.username || url.password) return null;
    const name = item.name.trim().slice(0, 100);
    return name && {name, url: url.href, description: typeof item.description === "string" ? item.description.slice(0, 200) : ""};
  } catch {
    return null;
  }
}

function render() {
  const combined = new Map([...configured, ...saved].map(item => [item.url, item]));
  list.replaceChildren();
  for (const item of combined.values()) {
    const row = document.createElement("li");
    const copy = document.createElement("div");
    const link = document.createElement("a");
    link.href = item.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = item.name;
    copy.append(link);
    if (item.description) {
      const note = document.createElement("small");
      note.textContent = item.description;
      copy.append(note);
    }
    row.append(copy);
    if (saved.some(savedItem => savedItem.url === item.url)) {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "secondary";
      remove.textContent = "Remove";
      remove.setAttribute("aria-label", "Remove " + item.name);
      remove.addEventListener("click", () => {
        saved = saved.filter(savedItem => savedItem.url !== item.url);
        persist();
        status.textContent = "Removed from your saved links.";
        render();
      });
      row.append(remove);
    }
    list.append(row);
  }
  empty.hidden = combined.size > 0;
}

function persist() {
  try { localStorage.setItem(storageKey, JSON.stringify(saved)); return true; }
  catch { return false; }
}

try {
  const entries = JSON.parse(localStorage.getItem(storageKey) || "[]");
  if (Array.isArray(entries)) saved = entries.map(normalized).filter(Boolean);
} catch { /* The current page can still use the configured links. */ }

form.addEventListener("submit", event => {
  event.preventDefault();
  const name = form.elements.namedItem("libraryName").value;
  const value = form.elements.namedItem("libraryUrl").value.trim();
  const entry = normalized({name, url: value.includes("://") ? value : "https://" + value});
  if (!entry) {
    status.textContent = "Enter a name and a valid web link.";
    return;
  }
  if (saved.some(item => item.url === entry.url) || configured.some(item => item.url === entry.url)) {
    status.textContent = "That library is already listed.";
    return;
  }
  saved.push(entry);
  status.textContent = persist() ? "Library added." : "Library added for this session.";
  form.reset();
  render();
});

render();
fetch("/api/static-libraries").then(response => response.ok ? response.json() : []).then(items => {
  if (Array.isArray(items)) configured = items.map(normalized).filter(Boolean);
  render();
}).catch(() => {});
