// The players page. Needs common.js (api, setStatus, startWakeHint, formatSeason, fillOptions) loaded first.

const tabLeaders = document.getElementById("tab-leaders");
const tabSearch = document.getElementById("tab-search");
const panelLeaders = document.getElementById("panel-leaders");
const panelSearch = document.getElementById("panel-search");

const statSelect = document.getElementById("stat");
const competitionSelect = document.getElementById("competition");
const seasonSelect = document.getElementById("season");
const leadersResult = document.getElementById("leaders-result");
const leadersTitle = document.getElementById("leaders-title");
const leadersHead = document.getElementById("leaders-head");
const leadersBody = document.getElementById("leaders-body");

const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const searchResults = document.getElementById("search-results");

const careerSection = document.getElementById("career");
const careerTitle = document.getElementById("career-title");
const careerSummary = document.getElementById("career-summary");
const careerHead = document.getElementById("career-head");
const careerBody = document.getElementById("career-body");
const expandAllButton = document.getElementById("expand-all");

const STAT_NAMES = {
  goals: "goals", assists: "assists", clean_sheets: "clean sheets", games: "games played", minutes: "minutes played",
};

let leadersRequest = 0;  // each of these lets us ignore a slow answer that has been replaced
let searchRequest = 0;
let careerRequest = 0;
let searchTimer = null;
let leadersShown = false;  // is there a leaders table ready to show?


// ---------- small helpers ----------

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function cell(text, className) {
  return el("td", text === null || text === undefined ? "-" : text, className);
}

function headerRow(columns) {
  // columns: [{label, title, className}]
  const tr = document.createElement("tr");
  for (const col of columns) {
    const th = el("th", col.label, col.className);
    th.scope = "col";
    if (col.title) th.title = col.title;
    tr.appendChild(th);
  }
  return tr;
}

function numberText(value) {
  return value === null || value === undefined ? "-" : Number(value).toLocaleString("en-CA");
}

function seasonRange(first, last) {
  return first === last ? formatSeason(first) : formatSeason(first) + " to " + formatSeason(last);
}


// ---------- tabs ----------

function showTab(name) {
  const leaders = name === "leaders";
  tabLeaders.setAttribute("aria-selected", String(leaders));
  tabSearch.setAttribute("aria-selected", String(!leaders));
  panelLeaders.hidden = !leaders;
  panelSearch.hidden = leaders;
  leadersResult.hidden = !(leaders && leadersShown);  // the leaders table belongs to the Leaders tab
  setStatus("", "");
  if (leaders) {
    searchInput.blur();
  } else {
    searchInput.focus();
  }
}

tabLeaders.addEventListener("click", () => showTab("leaders"));
tabSearch.addEventListener("click", () => showTab("search"));


// ---------- leaders ----------

function showLeaders(data) {
  const stat = data.stat;
  const keeper = stat === "clean_sheets";

  const columns = [
    { label: "#", title: "Rank", className: "pos" },
    { label: "Player", className: "team" },
    { label: "Gm", title: "Games played", className: stat === "games" ? "key" : "" },
    { label: "Min", title: "Minutes played", className: stat === "minutes" ? "key hide-sm" : "hide-sm" },
  ];
  if (keeper) {
    columns.push({ label: "CS", title: "Clean sheets", className: "key" });
  } else {
    columns.push({ label: "G", title: "Goals", className: stat === "goals" ? "key" : "" });
    columns.push({ label: "A", title: "Assists", className: stat === "assists" ? "key" : "" });
  }
  leadersHead.innerHTML = "";
  leadersHead.appendChild(headerRow(columns));

  leadersBody.innerHTML = "";
  for (const p of data.players) {
    const tr = document.createElement("tr");
    tr.appendChild(cell(p.rank, "pos"));

    const nameCell = el("td", null, "team");
    const button = el("button", p.player_name, "link-button");
    button.type = "button";
    button.addEventListener("click", () => showCareer(p.player_id, p.player_name));
    nameCell.appendChild(button);
    nameCell.appendChild(el("span", p.clubs, "sub"));
    tr.appendChild(nameCell);

    tr.appendChild(cell(numberText(p.games), stat === "games" ? "key" : ""));
    tr.appendChild(cell(numberText(p.minutes), stat === "minutes" ? "key hide-sm" : "hide-sm"));
    if (keeper) {
      tr.appendChild(cell(numberText(p.clean_sheets), "key"));
    } else {
      tr.appendChild(cell(numberText(p.goals), stat === "goals" ? "key" : ""));
      tr.appendChild(cell(numberText(p.assists), stat === "assists" ? "key" : ""));
    }
    leadersBody.appendChild(tr);
  }

  const compName = competitionSelect.selectedOptions[0] ? competitionSelect.selectedOptions[0].textContent : "";
  const seasonName = seasonSelect.selectedOptions[0] ? seasonSelect.selectedOptions[0].textContent : "";
  leadersTitle.textContent = "Most " + STAT_NAMES[stat] + ", " + compName + ", " + seasonName;
  leadersShown = true;
  leadersResult.hidden = panelLeaders.hidden;
}

async function loadLeaders() {
  const myRequest = ++leadersRequest;
  if (!competitionSelect.value || !seasonSelect.value) return;

  leadersShown = false;
  leadersResult.hidden = true;
  const stopHint = startWakeHint("Loading the leaders...");
  try {
    const path = "/top-players?stat=" + encodeURIComponent(statSelect.value)
      + "&competition=" + encodeURIComponent(competitionSelect.value)
      + "&season=" + encodeURIComponent(seasonSelect.value)
      + "&limit=20";
    const data = await api(path);
    if (myRequest !== leadersRequest) return;
    if (data.players.length === 0) {
      setStatus("No players to show for this choice.", "");
      return;
    }
    setStatus("", "");
    showLeaders(data);
  } catch (err) {
    if (myRequest !== leadersRequest) return;
    setStatus(err.message, "error");
  } finally {
    stopHint();
  }
}

async function loadFilters() {
  const stopHint = startWakeHint("Loading competitions and seasons...");
  try {
    const [comps, seasons] = await Promise.all([api("/player-competitions"), api("/player-seasons")]);
    stopHint();

    fillOptions(competitionSelect, [
      ...comps.competitions.map((c) => ({ value: c.id, label: c.name })),
      { value: "all", label: "All competitions" },
    ]);
    fillOptions(seasonSelect, [
      ...seasons.seasons.map((s) => ({ value: s, label: formatSeason(s) })),
      { value: "all", label: "All seasons" },
    ]);

    // start on the Premier League, newest season, if it exists
    if (comps.competitions.some((c) => c.id === "GB1")) competitionSelect.value = "GB1";
    await loadLeaders();
  } catch (err) {
    stopHint();
    setStatus(err.message, "error");
  }
}

statSelect.addEventListener("change", loadLeaders);
competitionSelect.addEventListener("change", loadLeaders);
seasonSelect.addEventListener("change", loadLeaders);


// ---------- player career ----------

function statCells(keeper, values, rowKind) {
  // the number cells shared by season rows and competition rows
  const cells = [
    cell(numberText(values.games)),
    cell(numberText(values.minutes), "hide-sm"),
  ];
  if (keeper) {
    cells.push(cell(numberText(values.clean_sheets), "key"));
  } else {
    cells.push(cell(numberText(values.goals), "key"));
    cells.push(cell(numberText(values.assists), "key"));
  }
  return cells;
}

function setSeasonOpen(button, children, open) {
  button.setAttribute("aria-expanded", String(open));
  for (const row of children) row.hidden = !open;
}

function updateExpandAllLabel() {
  const buttons = [...careerBody.querySelectorAll(".toggle")];
  const allOpen = buttons.length > 0 && buttons.every((b) => b.getAttribute("aria-expanded") === "true");
  expandAllButton.textContent = allOpen ? "Collapse all seasons" : "Expand all seasons";
}

function showCareerRows(data) {
  const keeper = data.player.position === "Goalkeeper";

  const columns = [
    { label: "Season", className: "season-head" },
    { label: "Club and competition", className: "team" },
    { label: "Gm", title: "Games played" },
    { label: "Min", title: "Minutes played", className: "hide-sm" },
  ];
  if (keeper) {
    columns.push({ label: "CS", title: "Clean sheets", className: "key" });
  } else {
    columns.push({ label: "G", title: "Goals", className: "key" });
    columns.push({ label: "A", title: "Assists", className: "key" });
  }
  careerHead.innerHTML = "";
  careerHead.appendChild(headerRow(columns));

  // group the rows by season, keeping the order the API sent (newest season first)
  const bySeason = new Map();
  for (const r of data.rows) {
    if (!bySeason.has(r.season)) bySeason.set(r.season, []);
    bySeason.get(r.season).push(r);
  }

  careerBody.innerHTML = "";
  let games = 0, goals = 0, assists = 0, cleanSheets = 0;

  for (const [season, rows] of bySeason) {
    const total = { games: 0, minutes: 0, goals: 0, assists: 0, clean_sheets: 0 };
    for (const r of rows) {
      total.games += r.games;
      total.minutes += r.minutes;
      total.goals += r.goals;
      total.assists += r.assists;
      total.clean_sheets += r.clean_sheets || 0;
    }
    games += total.games; goals += total.goals; assists += total.assists; cleanSheets += total.clean_sheets;

    const clubs = [...new Set(rows.map((r) => r.club))].join(", ");

    // the season row: totals across every competition
    const seasonRow = document.createElement("tr");
    seasonRow.className = "season-row";

    const seasonCell = el("td", null, "season");
    const toggle = el("button", null, "toggle");
    toggle.type = "button";
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Show the " + rows.length + (rows.length === 1 ? " competition" : " competitions") + " for " + formatSeason(season));
    toggle.appendChild(el("span", null, "chev"));
    toggle.appendChild(document.createTextNode(formatSeason(season)));
    seasonCell.appendChild(toggle);
    seasonRow.appendChild(seasonCell);

    const clubCell = el("td", clubs, "team");
    clubCell.appendChild(el("span", rows.length + (rows.length === 1 ? " competition" : " competitions"), "sub"));
    seasonRow.appendChild(clubCell);
    for (const c of statCells(keeper, total)) seasonRow.appendChild(c);
    careerBody.appendChild(seasonRow);

    // one row per competition, hidden until the arrow is clicked
    const children = [];
    for (const r of rows) {
      const tr = document.createElement("tr");
      tr.className = "comp-row";
      tr.hidden = true;
      tr.appendChild(el("td"));
      const nameCell = el("td", r.competition, "team");
      nameCell.appendChild(el("span", r.club, "sub"));
      tr.appendChild(nameCell);
      for (const c of statCells(keeper, r)) tr.appendChild(c);
      careerBody.appendChild(tr);
      children.push(tr);
    }

    toggle.addEventListener("click", () => {
      setSeasonOpen(toggle, children, toggle.getAttribute("aria-expanded") !== "true");
      updateExpandAllLabel();
    });
  }
  updateExpandAllLabel();

  const seasons = [...bySeason.keys()].sort();
  const span = seasonRange(seasons[0], seasons[seasons.length - 1]);
  careerSummary.textContent = keeper
    ? numberText(cleanSheets) + " clean sheets in " + numberText(games) + " games, " + span + "."
    : numberText(goals) + " goals and " + numberText(assists) + " assists in " + numberText(games) + " games, " + span + ".";
}

expandAllButton.addEventListener("click", () => {
  const buttons = [...careerBody.querySelectorAll(".toggle")];
  const open = !buttons.every((b) => b.getAttribute("aria-expanded") === "true");
  for (const button of buttons) {
    const seasonRow = button.closest("tr");
    const children = [];
    for (let row = seasonRow.nextElementSibling; row && row.classList.contains("comp-row"); row = row.nextElementSibling) {
      children.push(row);
    }
    setSeasonOpen(button, children, open);
  }
  updateExpandAllLabel();
});

async function showCareer(playerId, name) {
  const myRequest = ++careerRequest;
  careerTitle.textContent = name;
  careerSummary.textContent = "";
  careerSection.hidden = true;
  const stopHint = startWakeHint("Loading " + name + "...");
  try {
    const data = await api("/player/" + encodeURIComponent(playerId));
    if (myRequest !== careerRequest) return;
    setStatus("", "");
    careerTitle.textContent = data.player.name;
    showCareerRows(data);
    careerSection.hidden = false;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    careerSection.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
  } catch (err) {
    if (myRequest !== careerRequest) return;
    setStatus(err.message, "error");
  } finally {
    stopHint();
  }
}


// ---------- search ----------

function showSearchResults(data) {
  searchResults.innerHTML = "";
  for (const p of data.players) {
    const item = document.createElement("li");
    const button = el("button", null, "result");
    button.type = "button";
    button.appendChild(el("span", p.player_name, "result-name"));
    const detail = [p.position, seasonRange(p.first_season, p.last_season), numberText(p.goals) + " goals, " + numberText(p.assists) + " assists"]
      .filter(Boolean).join(", ");
    button.appendChild(el("span", detail, "sub"));
    button.addEventListener("click", () => showCareer(p.player_id, p.player_name));
    item.appendChild(button);
    searchResults.appendChild(item);
  }
}

async function runSearch() {
  const query = searchInput.value.trim();
  const myRequest = ++searchRequest;
  searchResults.innerHTML = "";
  if (query.length < 2) {
    setStatus("", "");
    return;
  }

  const stopHint = startWakeHint("Searching...");
  try {
    const data = await api("/player-search?q=" + encodeURIComponent(query));
    if (myRequest !== searchRequest) return;
    if (data.players.length === 0) {
      setStatus("No players found for \"" + query + "\". Check the spelling, including accents.", "");
      return;
    }
    setStatus("", "");
    showSearchResults(data);
  } catch (err) {
    if (myRequest !== searchRequest) return;
    setStatus(err.message, "error");
  } finally {
    stopHint();
  }
}

searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(runSearch, 350);  // wait until typing pauses
});
searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  clearTimeout(searchTimer);
  runSearch();
});


// ---------- start ----------

loadFilters();
