// Change this one line if the API address ever changes.
const API_URL = "https://premier-league-predictor-138n.onrender.com";

const form = document.getElementById("predict-form");
const leagueSelect = document.getElementById("league");
const homeSelect = document.getElementById("home");
const awaySelect = document.getElementById("away");
const predictBtn = document.getElementById("predict-btn");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");

let teams = [];       // teams for the selected league
let teamsRequest = 0; // lets us ignore a slow answer if the league was changed again


// ---------- helpers ----------

// Call the API and return the parsed JSON. Throws an Error with a readable message.
async function api(path) {
  let response;
  try {
    response = await fetch(API_URL + path);
  } catch (err) {
    // fetch only throws when it can't reach the server at all
    throw new Error("Can't reach the prediction server. Check your connection and try again.");
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    // FastAPI sends errors as {"detail": "..."}
    const detail = data && typeof data.detail === "string" ? data.detail : null;
    throw new Error(detail || "The server returned an error (status " + response.status + "). Try again in a moment.");
  }
  return data;
}

// kind is "", "loading" or "error"
function setStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = "status" + (kind ? " " + kind : "");
}

// The free host goes to sleep when idle, so the first request can be slow.
// If a request is still running after 4 seconds, explain why. Returns a function that cancels the hint.
function startWakeHint(message) {
  setStatus(message, "loading");
  const timer = setTimeout(() => {
    setStatus("Waking up the server. The free host sleeps when idle, so this can take up to a minute.", "loading");
  }, 4000);
  return () => clearTimeout(timer);
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

// Fill a list with "Over 2.5 ........ 61.3%" rows.
function fillLines(listId, overLines) {
  const list = document.getElementById(listId);
  list.innerHTML = "";
  for (const [line, chance] of Object.entries(overLines)) {
    const item = document.createElement("li");
    const label = document.createElement("span");
    const value = document.createElement("span");
    label.textContent = "Over " + line;
    value.textContent = chance + "%";
    item.appendChild(label);
    item.appendChild(value);
    list.appendChild(item);
  }
}

function showResult(data) {
  const { home, away, outcome, totals } = data;

  document.getElementById("result-title").textContent = home + " vs " + away;

  const rows = [
    { key: "home", label: home + " win", value: outcome.home_win },
    { key: "draw", label: "Draw", value: outcome.draw },
    { key: "away", label: away + " win", value: outcome.away_win },
  ];
  const highest = Math.max(...rows.map((row) => row.value));

  resultEl.hidden = false;

  for (const row of rows) {
    document.getElementById("label-" + row.key).textContent = row.label;
    document.getElementById("p-" + row.key).textContent = row.value + "%";
    const fill = document.getElementById("bar-" + row.key);
    fill.classList.toggle("top", row.value === highest);
    fill.style.width = "0%";
    // wait two frames so the browser sees 0% first, then animates to the real value
    requestAnimationFrame(() => {
      requestAnimationFrame(() => { fill.style.width = row.value + "%"; });
    });
  }

  document.getElementById("goals-expected").textContent = totals.goals.expected;
  document.getElementById("corners-expected").textContent = totals.corners.expected;
  fillLines("goals-lines", totals.goals.over);
  fillLines("corners-lines", totals.corners.over);

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  resultEl.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
}


// ---------- loading the dropdowns ----------

async function loadTeams() {
  const myRequest = ++teamsRequest;
  resultEl.hidden = true;
  predictBtn.disabled = true;
  const stopHint = startWakeHint("Loading teams...");

  try {
    const data = await api("/teams?league=" + encodeURIComponent(leagueSelect.value));
    if (myRequest !== teamsRequest) return; // the league changed again, ignore this answer
    teams = data.teams;
    fillSelect(homeSelect, teams);
    updateAwayOptions();

    if (teams.length < 2) {
      setStatus("Not enough teams found for this league.", "error");
    } else {
      setStatus("", "");
      predictBtn.disabled = false;
    }
  } catch (err) {
    if (myRequest !== teamsRequest) return;
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
    await loadTeams();
  } catch (err) {
    stopHint();
    setStatus(err.message, "error");
  }
}


// ---------- the Predict button ----------

async function predict() {
  const home = homeSelect.value;
  const away = awaySelect.value;
  if (!home || !away) {
    setStatus("Pick a home team and an away team first.", "error");
    return;
  }

  predictBtn.disabled = true;
  resultEl.hidden = true;
  const stopHint = startWakeHint("Building the prediction from each team's last five matches...");

  try {
    const url = "/predict?home=" + encodeURIComponent(home) + "&away=" + encodeURIComponent(away);
    const data = await api(url);
    stopHint();
    setStatus("", "");
    showResult(data);
  } catch (err) {
    // covers: server unreachable, and the API refusing (e.g. a team with no recent history)
    stopHint();
    setStatus(err.message, "error");
  } finally {
    predictBtn.disabled = false;
  }
}


// ---------- wiring it together ----------

leagueSelect.addEventListener("change", loadTeams);
homeSelect.addEventListener("change", updateAwayOptions);
form.addEventListener("submit", (event) => {
  event.preventDefault(); // stop the browser reloading the page
  predict();
});

loadLeagues();
