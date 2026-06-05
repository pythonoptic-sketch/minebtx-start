const scenarios = {
  change: {
    intent: "Change me to an earlier flight and keep my paid bag and seat. Ask before any extra charge above $250.",
    hero: "Move me to an earlier flight, keep my seat and bag, and stay under policy.",
    walletCap: 250,
    risk: "balanced",
    route: "SFO -> JFK",
    status: "Change path ready",
    score: 94,
    steps: [
      ["Reservation read", "PNR status, ticket coupon, fare basis, and current flight segment loaded.", "0.4s"],
      ["Ancillaries checked", "Bag and seat EMDs are mapped to the current ticket and evaluated for transfer.", "0.9s"],
      ["Rules applied", "Fare difference is under the approval cap and no refund value is destroyed.", "1.3s"],
      ["Action prepared", "Earlier flight can be held pending traveler confirmation.", "ready"],
    ],
    order: [
      ["P", "Passenger", "Profile and loyalty attached", "verified"],
      ["F", "Flight product", "Earlier same-day option held", "actionable"],
      ["S", "Seat and bag", "EMDs checked for transfer", "protected"],
      ["$", "Payment", "Auto-charge capped at $250", "bounded"],
      ["R", "Allowed action", "Exchange ticket after consent", "ready"],
    ],
  },
  delay: {
    intent: "My flight is delayed and I will miss dinner. Rebook me, move the car pickup, update the hotel ETA, and notify the team.",
    hero: "My flight is delayed. Rebook the trip, move the car, update the hotel, and notify my team.",
    walletCap: 400,
    risk: "fast",
    route: "LAX -> ORD",
    status: "Recovery active",
    score: 91,
    steps: [
      ["Delay detected", "The monitoring loop flagged a missed-connection and dinner-arrival risk.", "live"],
      ["Waiver evaluated", "Airline schedule-change rules allow a same-day move without penalty.", "0.8s"],
      ["Downstream services moved", "Ride pickup, hotel ETA, and calendar notifications are staged.", "1.5s"],
      ["Human fallback ready", "Operator packet includes order context if supplier inventory disappears.", "ready"],
    ],
    order: [
      ["M", "Monitoring", "Delay, waiver, traffic, and hotel risk tracked", "live"],
      ["F", "Flight product", "Replacement flight ranked by arrival time", "ranked"],
      ["H", "Hotel", "Late arrival notice drafted", "staged"],
      ["C", "Car transfer", "Pickup time moved", "staged"],
      ["O", "Ops handoff", "Escalation packet prepared", "armed"],
    ],
  },
  new: {
    intent: "Plan a five-day Tokyo trip in October with boutique hotels, food-first neighborhoods, trains, and a flexible budget.",
    hero: "Plan five days in Tokyo with boutique hotels, food-first neighborhoods, trains, and a flexible budget.",
    walletCap: 1800,
    risk: "balanced",
    route: "Home -> Tokyo",
    status: "Draft order",
    score: 88,
    steps: [
      ["Intent structured", "Dates, trip style, budget, airport, neighborhoods, and food preferences parsed.", "0.5s"],
      ["Supply assembled", "Flights, hotel zones, train routing, restaurants, and activity holds created.", "1.9s"],
      ["Order drafted", "Cancellation windows, payment caps, and traveler approvals are attached.", "2.4s"],
      ["Consent required", "The agent will not book until the trip order and wallet cap are approved.", "hold"],
    ],
    order: [
      ["I", "Itinerary", "Five-day plan with editable blocks", "draft"],
      ["H", "Hotel", "Boutique zones compared", "ranked"],
      ["T", "Transport", "Flights, rail, and transfers bundled", "draft"],
      ["W", "Wallet", "Budget and approval rules attached", "pending"],
      ["A", "Allowed action", "Book after consent", "hold"],
    ],
  },
};

function money(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function setActiveScenario(name) {
  const scenario = scenarios[name] || scenarios.change;
  document.getElementById("order-intent").value = scenario.intent;
  document.getElementById("hero-intent").value = scenario.hero;
  document.getElementById("wallet-cap").value = scenario.walletCap;
  document.getElementById("risk-mode").value = scenario.risk;
  renderOrder(scenario);
  document.querySelectorAll("[data-scenario]").forEach((button) => {
    button.classList.toggle("active", button.dataset.scenario === name);
  });
}

function renderOrder(scenario) {
  document.getElementById("order-status").textContent = scenario.status;
  document.getElementById("order-route").textContent = scenario.route;
  document.getElementById("order-score").textContent = `${scenario.score}%`;

  document.getElementById("agent-steps").innerHTML = scenario.steps
    .map(([title, body, time]) => `
      <li>
        <i aria-hidden="true"></i>
        <span><strong>${escapeHtml(title)}</strong>${escapeHtml(body)}</span>
        <em>${escapeHtml(time)}</em>
      </li>
    `)
    .join("");

  document.getElementById("order-object").innerHTML = scenario.order
    .map(([icon, title, body, badge]) => `
      <article class="order-row">
        <i aria-hidden="true">${escapeHtml(icon)}</i>
        <span><strong>${escapeHtml(title)}</strong>${escapeHtml(body)}</span>
        <small>${escapeHtml(badge)}</small>
      </article>
    `)
    .join("");
}

function runCustomOrder() {
  const intent = document.getElementById("order-intent").value.trim();
  const walletCap = Number(document.getElementById("wallet-cap").value || 0);
  const risk = document.getElementById("risk-mode").value;
  const score = risk === "strict" ? 97 : risk === "fast" ? 89 : 93;
  const scenario = {
    route: intent.toLowerCase().includes("tokyo") ? "Home -> Tokyo" : "Trip order",
    status: "Custom order drafted",
    score,
    steps: [
      ["Intent translated", "The request was converted into products, rules, money movement, monitoring, and allowed actions.", "0.3s"],
      ["Order object built", `Wallet authority is capped at ${money(walletCap)} with the risk mode set to ${risk}.`, "0.8s"],
      ["Rules pending", "Production needs supplier fare, ticket, EMD, hotel, and refund APIs before this can transact.", "next"],
      ["Consent required", "Evarian asks before irreversible spend, forfeiture, or non-refundable changes.", "hold"],
    ],
    order: [
      ["I", "Intent", intent || "Traveler request", "parsed"],
      ["$", "Wallet", `Auto-approval capped at ${money(walletCap)}`, "bounded"],
      ["R", "Rules", "Fare, refund, EMD, and policy checks required", "pending"],
      ["M", "Monitoring", "Delay, traffic, weather, and supplier changes", "armed"],
      ["O", "Allowed action", "Modify after consent", "ready"],
    ],
  };
  renderOrder(scenario);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function submitWaitlist(email) {
  const payload = {
    email,
    source: "drinknile.com",
    product: "evarian-travel-os",
    joined_at: new Date().toISOString(),
  };
  const local = JSON.parse(localStorage.getItem("evarian_waitlist") || "[]");
  local.push(payload);
  localStorage.setItem("evarian_waitlist", JSON.stringify(local.slice(-50)));

  try {
    const response = await fetch("/api/waitlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return response.ok ? "server" : "local";
  } catch {
    return "local";
  }
}

document.querySelectorAll("[data-scenario]").forEach((button) => {
  button.addEventListener("click", () => setActiveScenario(button.dataset.scenario));
});

document.getElementById("run-order")?.addEventListener("click", runCustomOrder);

document.getElementById("hero-command-form")?.addEventListener("submit", (event) => {
  event.preventDefault();
  const intent = document.getElementById("hero-intent").value.trim();
  document.getElementById("order-intent").value = intent;
  runCustomOrder();
  document.getElementById("order")?.scrollIntoView({ behavior: "smooth", block: "start" });
});

document.getElementById("waitlist-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = document.getElementById("waitlist-email").value.trim();
  const message = document.getElementById("waitlist-message");
  if (!email) return;
  message.textContent = "Adding you...";
  const destination = await submitWaitlist(email);
  message.textContent = destination === "server"
    ? "You are on the waitlist. We will send product updates as the order layer comes online."
    : "Saved locally for now. The server waitlist endpoint will capture this once deployed.";
  event.target.reset();
});

setActiveScenario("change");
