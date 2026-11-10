// Change this one line when the API is deployed.
const API_URL = "http://127.0.0.1:8001";

const leagueSelect = document.getElementById("league");
const homeSelect = document.getElementById("home");
const awaySelect = document.getElementById("away");
const predictBtn = document.getElementById("predict-btn");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");

let teams = []; // teams for the selected league


// ---------- helpers ----------

// Call the API and return the parsed JSON. Throws an Error with a readable message.
async function api(path) {
  let response;
  try {
    response = await fetch(API_URL + path);
  } catch (err) {
    // fetch only throws when it can't reach the server at all
    throw new Error("Can't reach the API. Is it running?");
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    // FastAPI sends errors as {"detail": "..."}
    const detail = data && typeof data.detail === "string" ? data.detail : null;
    throw new Error(detail || "Request failed (status " + response.status + ")");
  }
  return data;
}

function setStatus(message, isError) {
  statusEl.textContent = message;
  statusEl.className = isError ? "error" : "";
}

// Replace a dropdown's options with a list of strings.
function fillSelect(select, items) {
  select.innerHTML = "";
  for (const item of items) {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    select.appendChild(option);
  }
}

// Away dropdown = every team except the chosen home team.
function updateAwayOptions() {
  const previousAway = awaySelect.value;
  const options = teams.filter((t) => t !== homeSelect.value);
  fillSelect(awaySelect, options);
  if (options.includes(previousAway)) {
    awaySelect.value = previousAway; // keep the user's choice if it is still valid
  }
}

// Fill a table body with "Over 2.5 | 61.3%" style rows.
function fillLines(tbodyId, overLines) {
  const tbody = document.getElementById(tbodyId);
  tbody.innerHTML = "";
  for (const [line, chance] of Object.entries(overLines)) {
    const row = document.createElement("tr");
    const lineCell = document.createElement("td");
    const chanceCell = document.createElement("td");
    lineCell.textContent = "Over " + line;
    chanceCell.textContent = chance + "%";
    row.appendChild(lineCell);
    row.appendChild(chanceCell);
    tbody.appendChild(row);
  }
}

function showResult(data) {
  const { home, away, outcome, totals } = data;

  document.getElementById("result-title").textContent = home + " vs " + away;
  document.getElementById("label-home").textContent = home + " win";
  document.getElementById("label-away").textContent = away + " win";
  document.getElementById("p-home").textContent = outcome.home_win + "%";
  document.getElementById("p-draw").textContent = outcome.draw + "%";
  document.getElementById("p-away").textContent = outcome.away_win + "%";

  document.getElementById("goals-expected").textContent = totals.goals.expected;
  document.getElementById("corners-expected").textContent = totals.corners.expected;
  fillLines("goals-lines", totals.goals.over);
  fillLines("corners-lines", totals.corners.over);

  resultEl.hidden = false;
}


// ---------- loading the dropdowns ----------

async function loadTeams() {
  resultEl.hidden = true;
  setStatus("Loading teams...", false);
  try {
    const data = await api("/teams?league=" + encodeURIComponent(leagueSelect.value));
    teams = data.teams;
    if (teams.length === 0) {
      setStatus("No teams found for this league.", true);
    } else {
      setStatus("", false);
    }
    fillSelect(homeSelect, teams);
    updateAwayOptions();
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function loadLeagues() {
  try {
    const leagues = await api("/leagues");
    fillSelect(leagueSelect, leagues);
    await loadTeams();
  } catch (err) {
    setStatus(err.message, true);
  }
}


// ---------- the Predict button ----------

async function predict() {
  const home = homeSelect.value;
  const away = awaySelect.value;
  if (!home || !away) {
    setStatus("Pick a home team and an away team first.", true);
    return;
  }

  predictBtn.disabled = true;
  resultEl.hidden = true;
  setStatus("Building features from the latest matches...", false);

  try {
    const url = "/predict?home=" + encodeURIComponent(home) + "&away=" + encodeURIComponent(away);
    const data = await api(url);
    setStatus("", false);
    showResult(data);
  } catch (err) {
    // covers: API down, and the API refusing (e.g. a team with no recent history)
    setStatus(err.message, true);
  } finally {
    predictBtn.disabled = false;
  }
}


// ---------- wiring it together ----------

leagueSelect.addEventListener("change", loadTeams);
homeSelect.addEventListener("change", updateAwayOptions);
predictBtn.addEventListener("click", predict);

loadLeagues();