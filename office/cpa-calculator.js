const form = document.querySelector("#cpa-form");
const results = document.querySelector("#cpa-results");
const values = document.querySelector("#cpa-values");
const status = document.querySelector("#cpa-status");
let summary = "";
let inputVersion = 0;

form.addEventListener("input", () => {
  inputVersion++;
  results.hidden = true;
  status.textContent = "";
});

form.addEventListener("submit", async event => {
  event.preventDefault();
  const submit = form.querySelector('button[type="submit"]');
  const version = inputVersion;
  const payload = Object.fromEntries(new FormData(form));
  if (!payload.profit_target) delete payload.profit_target;
  submit.disabled = true;
  results.hidden = true;
  status.textContent = "";
  try {
    const response = await fetch("/api/cpa", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "The calculator couldn’t use those inputs.");
    if (version !== inputVersion) return;
    const money = value => `${result.currency} ${value}`;
    const rows = [
      ["Break-even CPA", result.break_even_cpa === null ? "No break-even CPA" : money(result.break_even_cpa)],
      ["Target CPA", result.target_cpa === null ? "Target exceeds available contribution" : money(result.target_cpa)],
      ["Break-even ROAS", result.break_even_roas === null ? "Unavailable" : `${result.break_even_roas}×`],
      ["Contribution before ads", money(result.pre_ad_contribution)],
      ["Variable costs", money(result.variable_costs)]
    ];
    values.replaceChildren(...rows.map(([label, value]) => {
      const row = document.createElement("div");
      const term = document.createElement("dt");
      const definition = document.createElement("dd");
      term.textContent = label;
      definition.textContent = value;
      row.append(term, definition);
      return row;
    }));
    summary = [
      "First-order acquisition economics. Fixed costs and repeat purchases are excluded.",
      `Revenue per order: ${money(payload.revenue)}. Contribution to keep per order: ${money(result.profit_target)}.`,
      ...rows.map(([label, value]) => `${label}: ${value}`)
    ].join("\n");
    results.hidden = false;
    status.textContent = "Results ready.";
  } catch (error) {
    if (version !== inputVersion) return;
    status.textContent = error instanceof TypeError
      ? "Open Local Tools through the Evolve HQ launcher to use the calculator."
      : error.message;
  } finally {
    submit.disabled = false;
  }
});

document.querySelector("#copy-cpa").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(summary);
    status.textContent = "Results copied.";
  } catch {
    status.textContent = "Select the values to copy them.";
  }
});
