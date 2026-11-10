// Shared by every page that talks to the API.

// Change this one line if the API address ever changes.
const API_URL = "https://premier-league-predictor-138n.onrender.com";

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

// Show a message in the element with id="status". kind is "", "loading" or "error".
function setStatus(message, kind) {
  const statusEl = document.getElementById("status");
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

// The database stores seasons as 2122. Show them as 21/22.
function formatSeason(code) {
  const text = String(code);
  return /^\d{4}$/.test(text) ? text.slice(0, 2) + "/" + text.slice(2) : text;
}

// Replace a dropdown's options with {value, label} pairs.
function fillOptions(select, options) {
  select.innerHTML = "";
  for (const { value, label } of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  }
}
