// The standings page. Needs common.js (API_URL, api, setStatus, startWakeHint, fillSelect) loaded first.

const leagueSelect = document.getElementById("league");
const seasonSelect = document.getElementById("season");
const resultEl = document.getElementById("result");
const tableTitle = document.getElementById("table-title");
const tableBody = document.getElementById("table-body");

let seasonsRequest = 0; // lets us ignore a slow answer if the league was changed again
let tableRequest = 0;   // same idea for the table


// ---------- helpers ----------

function cell(text, className) {
  const td = document.createElement("td");
  td.textContent = text;
  if (className) td.className = className;
  return td;
}

// +12, 0, -7
function formatGoalDifference(value) {
  return value > 0 ? "+" + value : String(value);
}

function showTable(data) {
  tableTitle.textContent = data.league + ", " + formatSeason(data.season);
  tableBody.innerHTML = "";

  for (const row of data.table) {
    const tr = document.createElement("tr");
    tr.appendChild(cell(row.position, "pos"));
    tr.appendChild(cell(row.team, "team"));
    tr.appendChild(cell(row.played));
    tr.appendChild(cell(row.won));
    tr.appendChild(cell(row.drawn));
    tr.appendChild(cell(row.lost));
    tr.appendChild(cell(row.gf));
    tr.appendChild(cell(row.ga));
    tr.appendChild(cell(formatGoalDifference(row.gd)));
    tr.appendChild(cell(row.points, "pts"));
    tableBody.appendChild(tr);
  }

  resultEl.hidden = false;
}


// ---------- loading data ----------

async function loadTable() {
  const myRequest = ++tableRequest;
  const league = leagueSelect.value;
  const season = seasonSelect.value;
  if (!league || !season) return;

  resultEl.hidden = true;
  const stopHint = startWakeHint("Loading the table...");

  try {
    const path = "/standings?league=" + encodeURIComponent(league) + "&season=" + encodeURIComponent(season);
    const data = await api(path);
    if (myRequest !== tableRequest) return; // something newer was requested, ignore this answer
    setStatus("", "");
    showTable(data);
  } catch (err) {
    if (myRequest !== tableRequest) return;
    setStatus(err.message, "error");
  } finally {
    stopHint();
  }
}

async function loadSeasons() {
  const myRequest = ++seasonsRequest;
  const previousSeason = seasonSelect.value;
  resultEl.hidden = true;
  const stopHint = startWakeHint("Loading seasons...");

  try {
    const data = await api("/seasons?league=" + encodeURIComponent(leagueSelect.value));
    if (myRequest !== seasonsRequest) return; // the league changed again, ignore this answer

    seasonSelect.innerHTML = "";
    for (const code of data.seasons) {
      const option = document.createElement("option");
      option.value = code;                      // what the API expects
      option.textContent = formatSeason(code);  // what people read
      seasonSelect.appendChild(option);
    }
    if (data.seasons.length === 0) {
      setStatus("No seasons found for this league.", "error");
      return;
    }
    if (data.seasons.includes(previousSeason)) {
      seasonSelect.value = previousSeason; // keep the user's season when switching league
    }
    stopHint();
    await loadTable();
  } catch (err) {
    if (myRequest !== seasonsRequest) return;
    setStatus(err.message, "error");
  } finally {
    stopHint();
  }
}

async function loadLeagues() {
  const stopHint = startWakeHint("Loading leagues...");
  try {
    const leagues = await api("/leagues");
    stopHint();
    fillSelect(leagueSelect, leagues);
    await loadSeasons();
  } catch (err) {
    stopHint();
    setStatus(err.message, "error");
  }
}


// ---------- wiring it together ----------

leagueSelect.addEventListener("change", loadSeasons);
seasonSelect.addEventListener("change", loadTable);

loadLeagues();
