#!/usr/bin/env node

const fs = require("fs");

const outputPath = process.argv[2] || "vast-offers.json";
const vastApiUrl = "https://console.vast.ai/api/v0/bundles/";
const vastApiKey = process.env.VAST_API_KEY || process.env.VAST_AI_API_KEY || "";

const requestBody = {
  limit: Number(process.env.VAST_OFFERS_LIMIT || 80),
  type: "on-demand",
  verified: { eq: true },
  rentable: { eq: true },
  rented: { eq: false },
  num_gpus: { gte: 1 },
  cpu_arch: { eq: "amd64" },
};

function pickNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function pickBoolean(value) {
  return typeof value === "boolean" ? value : null;
}

function normalizeOffer(offer) {
  return {
    id: offer.id,
    ask_contract_id: offer.ask_contract_id,
    machine_id: offer.machine_id,
    host_id: offer.host_id,
    gpu_name: offer.gpu_name,
    num_gpus: pickNumber(offer.num_gpus),
    gpu_ram_mb: pickNumber(offer.gpu_ram),
    gpu_total_ram_mb: pickNumber(offer.gpu_total_ram),
    compute_cap: pickNumber(offer.compute_cap),
    cuda_max_good: pickNumber(offer.cuda_max_good),
    driver_version: offer.driver_version || null,
    dph_total: pickNumber(offer.dph_total),
    dph_base: pickNumber(offer.dph_base),
    discounted_dph_total: pickNumber(offer.discounted_dph_total),
    min_bid: pickNumber(offer.min_bid),
    geolocation: offer.geolocation || null,
    reliability: pickNumber(offer.reliability),
    reliability2: pickNumber(offer.reliability2),
    duration_s: pickNumber(offer.duration),
    time_remaining_s: pickNumber(offer.time_remaining),
    direct_port_count: pickNumber(offer.direct_port_count),
    static_ip: pickBoolean(offer.static_ip),
    internet_down_mbps: pickNumber(offer.inet_down),
    internet_up_mbps: pickNumber(offer.inet_up),
    cpu_cores_effective: pickNumber(offer.cpu_cores_effective),
    cpu_ram_mb: pickNumber(offer.cpu_ram),
    disk_space_gb: pickNumber(offer.disk_space),
    verification: offer.verification || null,
    rentable: pickBoolean(offer.rentable),
    rented: pickBoolean(offer.rented),
  };
}

function buildHeaders() {
  const headers = { "content-type": "application/json" };
  if (vastApiKey) headers.authorization = `Bearer ${vastApiKey}`;
  return headers;
}

async function main() {
  const response = await fetch(vastApiUrl, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    throw new Error(`Vast API request failed: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  const offers = Array.isArray(data.offers) ? data.offers : [];
  if (!offers.length) {
    throw new Error("Vast API returned no offers");
  }

  const normalized = offers
    .map(normalizeOffer)
    .filter((offer) => offer.id && offer.gpu_name && Number.isFinite(offer.dph_total))
    .sort((left, right) => left.dph_total - right.dph_total);

  const payload = {
    source: vastApiUrl,
    source_name: "Vast.ai Search Offers API",
    fetched_at: new Date().toISOString(),
    authenticated_request: Boolean(vastApiKey),
    query: requestBody,
    offers: normalized,
  };

  fs.writeFileSync(outputPath, `${JSON.stringify(payload, null, 2)}\n`);
  console.log(`Wrote ${normalized.length} Vast offers to ${outputPath}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
