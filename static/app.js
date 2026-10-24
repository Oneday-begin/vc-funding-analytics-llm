"use strict";

const $ = (id) => document.getElementById(id);
const number = (value) => Number(value || 0).toLocaleString("en-US");
const money = (value) =>
  value == null
    ? "Undisclosed"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        notation: "compact",
        maximumFractionDigits: 2,
      }).format(value);
const billion = (value) =>
  "$" +
  Number(value || 0).toLocaleString("en-US", { maximumFractionDigits: 2 }) +
  "B";
const countryNames =
  typeof Intl.DisplayNames === "function"
    ? new Intl.DisplayNames(["en"], { type: "region" })
    : null;
const countryMap = {
  USA: "US",
  GBR: "GB",
  IND: "IN",
  CAN: "CA",
  DEU: "DE",
  CHN: "CN",
  FRA: "FR",
  ISR: "IL",
  AUS: "AU",
  JPN: "JP",
  SGP: "SG",
  BRA: "BR",
  NLD: "NL",
  CHE: "CH",
  SWE: "SE",
  ESP: "ES",
  KOR: "KR",
  RUS: "RU",
  IRL: "IE",
  ITA: "IT",
  ZAF: "ZA",
  NZL: "NZ",
  HKG: "HK",
};
function countryName(code) {
  try {
    return countryMap[code] && countryNames
      ? countryNames.of(countryMap[code])
      : code || "Unknown";
  } catch {
    return code || "Unknown";
  }
}
function node(tag, text, className) {
  const n = document.createElement(tag);
  if (text != null) n.textContent = text;
  if (className) n.className = className;
  return n;
}
function append(parent, ...children) {
  parent.append(...children);
  return parent;
}
function clear(id) {
  const element = $(id);
  element.replaceChildren();
  return element;
}
let toastTimer;
function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("toast").hidden = true), 4500);
}

async function getJSON(path, params = {}, options = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== "" && v != null),
  );
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 55000);
  try {
    const response = await fetch(path + (query.size ? "?" + query : ""), {
      ...options,
      signal: controller.signal,
      headers: { Accept: "application/json", ...(options.headers || {}) },
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error(
        "The server is starting or temporarily unavailable. Please try again shortly.",
      );
    }
    if (!response.ok)
      throw new Error(data.error || "The request could not be completed.");
    return data;
  } catch (error) {
    if (error.name === "AbortError")
      throw new Error(
        "The request timed out. The free server may be waking up; please try again.",
      );
    if (error instanceof TypeError)
      throw new Error(
        "Could not reach the data service. Check your connection and try again.",
      );
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

async function landing() {
  const results = await Promise.allSettled([
    getJSON("/api/metadata"),
    getJSON("/api/top-markets"),
  ]);
  if (results[0].status === "fulfilled")
    document
      .querySelectorAll("[data-metric]")
      .forEach(
        (el) => (el.textContent = number(results[0].value[el.dataset.metric])),
      );
  const target = clear("landing-markets");
  if (results[1].status === "fulfilled" && results[1].value.length) {
    const rows = results[1].value.slice(0, 4),
      maximum = rows[0].total_funding_bn;
    rows.forEach((row) => {
      const block = node("div", null, "preview-row");
      const label = append(
        node("div", null, "preview-label"),
        node("span", row.market),
        node("strong", billion(row.total_funding_bn)),
      );
      const fill = node("div", null, "preview-fill");
      fill.style.width = (100 * row.total_funding_bn) / maximum + "%";
      block.append(label, append(node("div", null, "preview-track"), fill));
      target.append(block);
    });
  } else {
    const retry = node("button", "Retry loading the dataset ↻", "text-link");
    retry.addEventListener("click", landing);
    append(
      target,
      node(
        "p",
        "The data service is taking a moment to respond.",
        "empty-state",
      ),
      retry,
    );
  }
}

function svgNode(tag, attrs = {}) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  return el;
}
let trendData = null;
function drawCohorts(data) {
  trendData = data;
  const target = clear("cohort-chart"),
    legend = clear("chart-legend");
  if (!data.labels.length || !data.datasets.length) {
    target.append(
      node("p", "No dated, funded records match these filters.", "empty-state"),
    );
    return;
  }
  const cumulative = $("chart-mode").value === "cumulative";
  const series = data.datasets.map((s) => ({
    ...s,
    values: s.data.map((value, i) =>
      cumulative ? value : value - (i ? s.data[i - 1] : 0),
    ),
  }));
  const max = Math.max(...series.flatMap((s) => s.values), 1),
    ceiling =
      Math.ceil(max / 10 ** Math.floor(Math.log10(max))) *
      10 ** Math.floor(Math.log10(max));
  const w = Math.max(300, target.clientWidth || 700),
    h = 245,
    left = 57,
    right = 18,
    top = 19,
    bottom = 34,
    plotW = w - left - right,
    plotH = h - top - bottom;
  const x = (i) =>
      left +
      (data.labels.length === 1
        ? plotW / 2
        : (i / (data.labels.length - 1)) * plotW),
    y = (v) => top + plotH - (v / ceiling) * plotH;
  const svg = svgNode("svg", {
    viewBox: `0 0 ${w} ${h}`,
    role: "img",
    "aria-label": `${cumulative ? "Cumulative lifetime" : "Lifetime"} funding by founding cohort for ${series.map((s) => s.label).join(", ")}. Values in millions of USD.`,
  });
  const title = svgNode("title");
  title.textContent = "Lifetime funding by company founding year";
  svg.append(title);
  for (let i = 0; i <= 4; i++) {
    const value = (ceiling * i) / 4,
      yy = y(value);
    svg.append(
      svgNode("line", {
        x1: left,
        y1: yy,
        x2: w - right,
        y2: yy,
        stroke: "#e3e6da",
        "stroke-width": 1,
      }),
    );
    const text = svgNode("text", {
      x: left - 10,
      y: yy + 3,
      "text-anchor": "end",
      fill: "#7a8275",
      "font-size": 9,
      "font-family": "Consolas, monospace",
    });
    text.textContent = money(value * 1e6);
    svg.append(text);
  }
  [
    ...new Set([
      0,
      Math.floor((data.labels.length - 1) / 4),
      Math.floor((data.labels.length - 1) / 2),
      Math.floor(((data.labels.length - 1) * 3) / 4),
      data.labels.length - 1,
    ]),
  ].forEach((i) => {
    const text = svgNode("text", {
      x: x(i),
      y: h - 12,
      "text-anchor": "middle",
      fill: "#7a8275",
      "font-size": 10,
      "font-family": "Consolas, monospace",
    });
    text.textContent = data.labels[i];
    svg.append(text);
  });
  series.forEach((s) => {
    const path = svgNode("path", {
      d: s.values
        .map(
          (v, i) => (i ? "L" : "M") + x(i).toFixed(2) + "," + y(v).toFixed(2),
        )
        .join(" "),
      fill: "none",
      stroke: s.borderColor,
      "stroke-width": 2.2,
      "stroke-linejoin": "round",
    });
    svg.append(path);
    const last = s.values.length - 1;
    const dot = svgNode("circle", {
      cx: x(last),
      cy: y(s.values[last]),
      r: 3,
      fill: s.borderColor,
    });
    const title = svgNode("title");
    title.textContent = `${s.label}, ${data.labels[last]}: ${money(s.values[last] * 1e6)}`;
    dot.append(title);
    svg.append(dot);
    const item = node("span");
    const swatch = node("i");
    swatch.style.background = s.borderColor;
    append(item, swatch, node("span", s.label));
    legend.append(item);
  });
  target.append(svg);
}

function drawCountries(rows) {
  const target = clear("concentration-bars");
  if (!rows.length) {
    target.append(
      node(
        "p",
        "No records meet the percentile threshold in this population. Try a broader filter.",
        "empty-state",
      ),
    );
    return;
  }
  const maximum = Math.max(...rows.map((r) => r.total_funding_bn), 0.001);
  rows.slice(0, 6).forEach((row) => {
    const line = node("div", null, "country-row");
    const label = node("span", row.country_code);
    label.title = countryName(row.country_code);
    const fill = node("div", null, "country-fill");
    fill.style.width =
      Math.max(1, (100 * row.total_funding_bn) / maximum) + "%";
    append(
      line,
      label,
      append(node("div", null, "country-track"), fill),
      node("strong", billion(row.total_funding_bn)),
    );
    target.append(line);
  });
}
function drawMarkets(rows) {
  const target = clear("markets-body"),
    sum = rows.reduce((a, r) => a + r.total_funding_bn, 0);
  if (!rows.length) {
    emptyRow(target, "No funded markets match these filters.", 6);
    return;
  }
  rows.forEach((row, i) => {
    const tr = node("tr");
    const name = node("button", row.market, "market-name company-link");
    name.addEventListener("click", () => {
      $("market").value = row.market;
      applyFilters();
    });
    const allocation = node("div", null, "allocation"),
      fill = node("div", null, "allocation-fill"),
      share = sum ? (100 * row.total_funding_bn) / sum : 0;
    fill.style.width = share + "%";
    append(
      allocation,
      append(node("div", null, "allocation-track"), fill),
      node("span", share.toFixed(1) + "%"),
    );
    append(
      tr,
      node("td", String(i + 1).padStart(2, "0"), "rank"),
      append(node("td"), name),
      node("td", billion(row.total_funding_bn), "numeric"),
      node("td", money(row.avg_funding_mn * 1e6), "numeric"),
      node("td", number(row.startup_count), "numeric"),
      append(node("td"), allocation),
    );
    target.append(tr);
  });
}
function drawStatuses(rows) {
  const target = clear("status-chart"),
    colors = {
      operating: "#275e4c",
      acquired: "#8499ae",
      closed: "#ba6543",
      unknown: "#c2c6b4",
    },
    total = rows.reduce((a, r) => a + r.total_funding_bn, 0);
  if (!total) {
    target.append(
      node("p", "No disclosed funding in this selection.", "empty-state"),
    );
    return;
  }
  const bar = node("div", null, "status-bar");
  bar.setAttribute("role", "img");
  bar.setAttribute(
    "aria-label",
    rows.map((r) => `${r.status}: ${billion(r.total_funding_bn)}`).join(", "),
  );
  const labels = node("div", null, "status-labels");
  rows.forEach((row) => {
    const segment = node("span");
    segment.style.width = (100 * row.total_funding_bn) / total + "%";
    segment.style.background = colors[row.status] || "#a5ae9b";
    bar.append(segment);
    const label = node("span"),
      swatch = node("i");
    swatch.style.background = segment.style.background;
    append(
      label,
      swatch,
      document.createTextNode(
        row.status.charAt(0).toUpperCase() + row.status.slice(1),
      ),
      node("strong", ((100 * row.total_funding_bn) / total).toFixed(1) + "%"),
    );
    labels.append(label);
  });
  append(target, bar, labels);
}
function emptyRow(target, message, columns) {
  const cell = node("td", message, "empty-state");
  cell.colSpan = columns;
  target.append(append(node("tr"), cell));
}

const filterKeys = ["market", "country", "status", "year_from", "year_to"];
let activeFilters = {},
  companyPage = 1,
  dashboardRevision = 0,
  companyRevision = 0,
  companyRows = new Map(),
  selectedCompany = null,
  currentNote = null,
  optionRevision = 0;
function syncURL() {
  const params = new URLSearchParams(activeFilters);
  if ($("company-search").value) params.set("q", $("company-search").value);
  if ($("company-sort").value !== "funding_desc")
    params.set("sort", $("company-sort").value);
  history.replaceState(
    null,
    "",
    location.pathname + (params.size ? "?" + params : "") + location.hash,
  );
}
function readFilters() {
  return Object.fromEntries(
    filterKeys.map((key) => [key, $(key).value]).filter(([, v]) => v !== ""),
  );
}
function applyFilters() {
  const form = $("filter-form");
  if (!form.reportValidity()) return;
  if (
    $("year_from").value &&
    $("year_to").value &&
    Number($("year_from").value) > Number($("year_to").value)
  ) {
    toast("The first founding year must be before the last.");
    return;
  }
  activeFilters = readFilters();
  companyPage = 1;
  syncURL();
  loadDashboard();
  loadCompanies();
}
async function loadDashboard() {
  const revision = ++dashboardRevision;
  $("loading-indicator").hidden = false;
  $("dashboard-error").hidden = true;
  const requests = [
    ["/api/stats", null],
    ["/api/funding-trends", "cohort-chart"],
    ["/api/top-markets", "markets-body"],
    ["/api/country-concentration", "concentration-bars"],
    ["/api/funding-by-status", "status-chart"],
  ];
  const results = await Promise.allSettled(
    requests.map(([url]) => getJSON(url, activeFilters)),
  );
  if (revision !== dashboardRevision) return;
  $("loading-indicator").hidden = true;
  const failed = results.find((r) => r.status === "rejected");
  if (failed) {
    $("dashboard-error").hidden = false;
    $("dashboard-error").querySelector("span").textContent =
      failed.reason.message;
  }
  results.forEach((result, i) => {
    if (result.status === "rejected") {
      if (i === 0) {
        [
          "stat-records",
          "stat-funding",
          "stat-markets",
          "stat-countries",
        ].forEach((id) => ($(id).textContent = "—"));
        $("stat-disclosed").textContent = "Data unavailable";
        $("stat-leading").textContent = "—";
      } else {
        const target = clear(requests[i][1]);
        if (i === 2)
          emptyRow(
            target,
            "Market analysis unavailable. Use “Try again” above.",
            6,
          );
        else
          target.append(
            node(
              "p",
              "Analysis unavailable. Use “Try again” above.",
              "empty-state",
            ),
          );
        if (i === 1) {
          clear("chart-legend");
          trendData = null;
        }
      }
      return;
    }
    const d = result.value;
    if (i === 0) {
      $("stat-records").textContent = number(d.total_records);
      $("stat-funding").textContent = billion(d.total_funding_bn);
      $("stat-markets").textContent = number(d.total_markets);
      $("stat-countries").textContent = number(d.total_countries);
      $("stat-disclosed").textContent =
        number(d.total_startups) + " with disclosed funding";
      $("stat-leading").textContent = d.top_market
        ? "Leading market: " + d.top_market
        : "No funded markets";
    } else if (i === 1) drawCohorts(d);
    else if (i === 2) drawMarkets(d);
    else if (i === 3) drawCountries(d);
    else drawStatuses(d);
  });
  const labels = Object.entries(activeFilters).map(([key, value]) =>
    key === "year_from"
      ? "Founded from " + value
      : key === "year_to"
        ? "Founded to " + value
        : key === "country"
          ? countryName(value)
          : value,
  );
  $("filter-summary").textContent =
    (labels.length ? labels.join(" · ") : "All records") +
    " · historical snapshot";
}
async function loadCompanies() {
  const revision = ++companyRevision,
    params = {
      ...activeFilters,
      q: $("company-search").value,
      sort: $("company-sort").value,
      page: companyPage,
      per_page: 12,
    };
  $("previous-page").disabled = true;
  $("next-page").disabled = true;
  const target = clear("companies-body");
  emptyRow(target, "Loading company records…", 6);
  const exportParams = new URLSearchParams({
    ...activeFilters,
    ...(params.q ? { q: params.q } : {}),
  });
  $("export-csv").href =
    "/api/companies/export.csv" + (exportParams.size ? "?" + exportParams : "");
  try {
    const data = await getJSON("/api/companies", params);
    if (revision !== companyRevision) return;
    target.replaceChildren();
    companyRows = new Map(data.records.map((r) => [r.id, r]));
    if (!data.records.length)
      emptyRow(
        target,
        "No companies match. Try another name or reset the dataset filters.",
        6,
      );
    data.records.forEach((row) => {
      const tr = node("tr"),
        link = node("button", null, "company-link");
      append(
        link,
        node(
          "span",
          (row.name || "?").slice(0, 1).toUpperCase(),
          "company-monogram",
        ),
        node("span", row.name || "Unnamed record"),
      );
      link.addEventListener("click", () => openProfile(row.id));
      const chip = node(
        "span",
        row.status || "Unknown",
        "status-chip " + (row.status || "unknown"),
      );
      append(
        tr,
        append(node("td"), link),
        node("td", row.market || "Unclassified"),
        node("td", row.country_code || "Unknown"),
        node("td", row.founded_year || "Unknown"),
        append(node("td"), chip),
        node("td", money(row.funding_total_usd), "numeric"),
      );
      target.append(tr);
    });
    $("company-count").textContent = data.total
      ? `${number((data.page - 1) * data.per_page + 1)}–${number(Math.min(data.page * data.per_page, data.total))} of ${number(data.total)} records`
      : "0 matching records";
    $("page-number").textContent =
      `Page ${data.page} of ${Math.max(1, data.pages)}`;
    $("previous-page").disabled = data.page <= 1;
    $("next-page").disabled = data.page >= data.pages;
  } catch (error) {
    if (revision !== companyRevision) return;
    target.replaceChildren();
    emptyRow(target, error.message, 6);
    $("company-count").textContent = "Directory unavailable";
    $("page-number").textContent = "—";
  }
}

async function openProfile(id) {
  try {
    const row = companyRows.get(id) || (await getJSON("/api/companies/" + id));
    selectedCompany = row;
    $("profile-title").textContent = row.name || "Unnamed company";
    const details = clear("profile-details");
    [
      ["Market", row.market || "Unclassified"],
      ["Country", countryName(row.country_code)],
      ["Founded", row.founded_year || "Unknown"],
      ["Recorded status", row.status || "Unknown"],
      ["Disclosed funding", money(row.funding_total_usd)],
      ["Profile type", "Historical record"],
    ].forEach(([label, value]) =>
      append(
        details,
        append(node("div"), node("dt", label), node("dd", value)),
      ),
    );
    $("company-dialog").showModal();
  } catch (error) {
    toast(error.message);
  }
}
function debounce(callback, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => callback(...args), delay);
  };
}
async function loadResearchOptions(preferred) {
  const revision = ++optionRevision;
  $("generate-button").disabled = true;
  try {
    const rows = await getJSON("/api/startups", {
      q: $("research-search").value,
    });
    if (revision !== optionRevision) return;
    const select = clear("research-company");
    if (preferred && !rows.some((row) => row.id === preferred.id))
      rows.unshift(preferred);
    rows.forEach((row) => {
      const option = node(
        "option",
        `${row.name} · ${row.market || "Unclassified"}`,
      );
      option.value = row.id;
      select.append(option);
    });
    if (!rows.length) {
      const option = node("option", "No funded companies found");
      option.value = "";
      select.append(option);
    }
    if (preferred) select.value = String(preferred.id);
    await updateSelectedProfile();
  } catch (error) {
    if (revision !== optionRevision) return;
    clear("research-company").append(
      node("option", "Company search unavailable"),
    );
    $("research-status").textContent = error.message;
  }
}
let profileRevision = 0;
async function updateSelectedProfile() {
  const revision = ++profileRevision,
    id = Number($("research-company").value);
  currentNote = null;
  $("research-result").hidden = true;
  $("research-empty").hidden = false;
  $("generate-button").disabled = true;
  if (!id) {
    $("selected-profile").textContent = "Select a funded company to begin.";
    return;
  }
  try {
    const row = await getJSON("/api/companies/" + id);
    if (revision !== profileRevision) return;
    $("selected-profile").textContent =
      `${countryName(row.country_code)} · Founded ${row.founded_year || "unknown"} · ${money(row.funding_total_usd)} disclosed`;
    $("generate-button").disabled = false;
  } catch (error) {
    if (revision === profileRevision)
      $("research-status").textContent = error.message;
  }
}
function showNote(record) {
  currentNote = record;
  $("research-empty").hidden = true;
  $("research-result").hidden = false;
  $("note-company").textContent = record.startup_name;
  $("note-thesis").textContent = record.investment_thesis;
  $("note-model").textContent = record.model_used;
  $("note-date").textContent = dateLabel(record.generated_at);
  $("save-note").textContent = "Save in this browser +";
}
function dateLabel(value) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? ""
    : date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
}
function readNotes() {
  try {
    const notes = JSON.parse(
      localStorage.getItem("venture-atlas-notes:v1") || "[]",
    );
    return Array.isArray(notes)
      ? notes
          .filter(
            (n) =>
              n &&
              typeof n.startup_name === "string" &&
              typeof n.investment_thesis === "string",
          )
          .slice(0, 20)
      : [];
  } catch {
    return [];
  }
}
function updateNoteCount() {
  $("saved-notes-count").textContent = readNotes().length;
}
function saveCurrentNote() {
  if (!currentNote) return;
  try {
    const notes = readNotes().filter(
      (n) => n.startup_id !== currentNote.startup_id,
    );
    notes.unshift(currentNote);
    localStorage.setItem(
      "venture-atlas-notes:v1",
      JSON.stringify(notes.slice(0, 20)),
    );
    updateNoteCount();
    $("save-note").textContent = "Saved in this browser ✓";
    toast("Research note saved on this device.");
  } catch {
    toast("Browser storage is unavailable. Use Copy note instead.");
  }
}
function noteText(note) {
  return `${note.startup_name} — Venture Atlas research note\n\n${note.investment_thesis}\n\nHistorical profile · ${note.model_used} · ${dateLabel(note.generated_at)}\nAI-generated; verify before use.\n${location.origin}/methodology`;
}
function openNotes() {
  const list = clear("saved-notes-list"),
    notes = readNotes();
  if (!notes.length)
    list.append(
      node(
        "p",
        "No saved notes yet. Generate a research note and select “Save in this browser”.",
        "empty-state",
      ),
    );
  notes.forEach((note) => {
    const block = node("article", null, "saved-note"),
      remove = node("button", "Remove note", "text-link");
    append(
      block,
      node("h3", note.startup_name),
      node("p", note.investment_thesis),
      node(
        "p",
        `${note.model_used} · ${dateLabel(note.generated_at)}`,
        "subtle",
      ),
    );
    remove.addEventListener("click", () => {
      try {
        localStorage.setItem(
          "venture-atlas-notes:v1",
          JSON.stringify(
            readNotes().filter((n) => n.startup_id !== note.startup_id),
          ),
        );
        updateNoteCount();
        openNotes();
      } catch {
        toast("Browser storage is unavailable.");
      }
    });
    block.append(remove);
    list.append(block);
  });
  if (!$("notes-dialog").open) $("notes-dialog").showModal();
}

async function workspace() {
  window.addEventListener(
    "resize",
    debounce(() => {
      if (trendData) drawCohorts(trendData);
    }, 150),
  );
  $("filter-form").addEventListener("submit", (event) => {
    event.preventDefault();
    applyFilters();
  });
  $("filter-form").addEventListener("reset", () => {
    setTimeout(applyFilters, 0);
  });
  $("retry-dashboard").addEventListener("click", () => {
    loadDashboard();
    loadCompanies();
  });
  $("chart-mode").addEventListener("change", () => {
    if (trendData) drawCohorts(trendData);
  });
  $("company-search").addEventListener(
    "input",
    debounce(() => {
      companyPage = 1;
      syncURL();
      loadCompanies();
    }),
  );
  $("company-sort").addEventListener("change", () => {
    companyPage = 1;
    syncURL();
    loadCompanies();
  });
  $("previous-page").addEventListener("click", () => {
    if (companyPage > 1) {
      companyPage--;
      loadCompanies();
    }
  });
  $("next-page").addEventListener("click", () => {
    companyPage++;
    loadCompanies();
  });
  document
    .querySelectorAll("[data-close]")
    .forEach((button) =>
      button.addEventListener("click", () => $(button.dataset.close).close()),
    );
  document.querySelectorAll("dialog").forEach((dialog) =>
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        const r = dialog.getBoundingClientRect();
        if (
          event.clientX < r.left ||
          event.clientX > r.right ||
          event.clientY < r.top ||
          event.clientY > r.bottom
        )
          dialog.close();
      }
    }),
  );
  $("profile-research").addEventListener("click", () => {
    if (!selectedCompany) return;
    $("company-dialog").close();
    $("research-search").value = selectedCompany.name || "";
    loadResearchOptions(selectedCompany);
    location.hash = "research";
  });
  $("research-search").addEventListener(
    "input",
    debounce(() => loadResearchOptions()),
  );
  $("research-company").addEventListener("change", updateSelectedProfile);
  $("research-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = $("generate-button"),
      id = Number($("research-company").value);
    if (!id) return;
    button.disabled = true;
    button.textContent = "Writing the research note…";
    $("research-company").disabled = true;
    $("research-search").disabled = true;
    $("research-status").textContent =
      "Reviewing the selected historical profile…";
    try {
      const data = await getJSON(
        "/api/generate-thesis",
        {},
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ startup_id: id }),
        },
      );
      showNote(data.record);
      $("research-status").textContent = data.cached
        ? "Retrieved the previously generated note for this company."
        : "A new research note is ready. Review the claims against the source profile.";
    } catch (error) {
      $("research-status").textContent = error.message;
    } finally {
      button.disabled = false;
      button.textContent = "Generate research note ↗";
      $("research-company").disabled = false;
      $("research-search").disabled = false;
    }
  });
  $("copy-note").addEventListener("click", async () => {
    if (!currentNote) return;
    try {
      await navigator.clipboard.writeText(noteText(currentNote));
      toast("Research note copied.");
    } catch {
      toast("Clipboard unavailable. You can select and copy the note text.");
    }
  });
  $("save-note").addEventListener("click", saveCurrentNote);
  $("open-saved-notes").addEventListener("click", openNotes);
  updateNoteCount();
  const params = new URLSearchParams(location.search);
  $("company-search").value = (params.get("q") || "").slice(0, 100);
  if (["funding_desc", "name_asc", "year_desc"].includes(params.get("sort")))
    $("company-sort").value = params.get("sort");
  try {
    const meta = await getJSON("/api/metadata");
    [
      ["market", meta.market_options],
      ["country", meta.country_options],
      ["status", meta.status_options],
    ].forEach(([id, values]) =>
      values.forEach((value) => {
        const option = node(
          "option",
          id === "country" ? countryName(value) + " (" + value + ")" : value,
        );
        option.value = value;
        $(id).append(option);
      }),
    );
    filterKeys.forEach((key) => {
      if (params.has(key)) {
        $(key).value = params.get(key);
        if ($(key).tagName === "SELECT" && !$(key).value) {
          const option = node("option", params.get(key));
          option.value = params.get(key);
          $(key).append(option);
          $(key).value = params.get(key);
        }
      }
    });
  } catch (error) {
    toast(error.message);
  }
  activeFilters = readFilters();
  loadDashboard();
  loadCompanies();
  loadResearchOptions();
  getJSON("/api/health")
    .then((data) => {
      $("connection-status").lastChild.textContent = " Data service connected";
      if (!data.ai_configured)
        $("research-status").textContent =
          "Live AI is not configured on this server. The company directory and analysis are available.";
    })
    .catch(() => {
      $("connection-status").lastChild.textContent =
        " Data service unavailable";
    });
}

if (document.body.dataset.page === "landing") landing();
if (document.body.dataset.page === "dashboard") workspace();
