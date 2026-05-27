const siteBaseUrl = "https://drinknile.com";
const installerUrl = `${siteBaseUrl}/install.sh`;
const statsUrl = "https://api.drinknile.com/stats";
const dashboardBaseUrl = "https://api.drinknile.com/dashboard";
const statsFallbackUrl = "stats-snapshot.json";
const treasuryUrl = "platform-treasury.json";
const vastOffersUrl = "vast-offers.json";
const vastReferralUrl = "vast-referral.json";
const placeholderAddress = "btx1z...YOUR_BTX_ADDRESS...";
const blockRewardBtx = 20;
const targetBlockSeconds = 90;
const blocksPerHour = 3600 / targetBlockSeconds;
const blocksPerDay = 86400 / targetBlockSeconds;
const btxModelPriceUsd = 5.707747399717103;
const referenceNetworkHashNps = 2_338_067;
let currentNetworkHashNps = referenceNetworkHashNps;
let currentPlatformFeeBps = 50;
let vastOffers = [];
let vastReferralConfig = null;

const formatNumber = new Intl.NumberFormat("en-US");
const formatBtx = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 8,
  maximumFractionDigits: 8,
});
const formatUsd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
const formatUsdPrice = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const formatUsdPrecise = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});

const gpuProfiles = [
  { gpu: "NVIDIA B200 SXM", arch: "Blackwell datacenter", profile: "16/8/128", nps: 260000, watts: 1000, confidence: "estimate", note: "large-die projection" },
  { gpu: "NVIDIA B100 SXM", arch: "Blackwell datacenter", profile: "16/8/128", nps: 210000, watts: 700, confidence: "estimate", note: "large-die projection" },
  { gpu: "NVIDIA H200 SXM", arch: "Hopper sm_90", profile: "16/8/128", nps: 160000, watts: 700, confidence: "estimate", note: "native sm_90 path" },
  { gpu: "NVIDIA H100 SXM", arch: "Hopper sm_90", profile: "16/8/128", nps: 145000, watts: 700, confidence: "estimate", note: "native sm_90 path" },
  { gpu: "NVIDIA RTX PRO 6000 Blackwell", arch: "Blackwell sm_120", profile: "16/8/128", nps: 125000, watts: 600, confidence: "estimate", note: "native sm_120 path" },
  { gpu: "NVIDIA H100 PCIe", arch: "Hopper sm_90", profile: "16/8/128", nps: 115000, watts: 350, confidence: "estimate", note: "native sm_90 path" },
  { gpu: "GeForce RTX 5090", arch: "Blackwell sm_120", profile: "16/8/128", nps: 105000, watts: 575, confidence: "estimate", note: "large-die projection" },
  { gpu: "NVIDIA RTX PRO 5000 Blackwell", arch: "Blackwell sm_120", profile: "16/8/128", nps: 76000, watts: 300, confidence: "estimate", note: "native sm_120 path" },
  { gpu: "GeForce RTX 4090", arch: "Ada sm_89", profile: "16/8/128", nps: 76000, watts: 450, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "GeForce RTX 5080", arch: "Blackwell sm_120", profile: "16/8/128", nps: 72000, watts: 360, confidence: "estimate", note: "native sm_120 path" },
  { gpu: "NVIDIA L40S", arch: "Ada sm_89", profile: "16/8/128", nps: 72000, watts: 350, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "NVIDIA RTX 6000 Ada", arch: "Ada sm_89", profile: "16/8/128", nps: 68000, watts: 300, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "NVIDIA L40", arch: "Ada sm_89", profile: "16/8/128", nps: 67000, watts: 300, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "GeForce RTX 4080 Super", arch: "Ada sm_89", profile: "16/8/128", nps: 59000, watts: 320, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "NVIDIA RTX PRO 4500 Blackwell", arch: "Blackwell sm_120", profile: "16/8/128", nps: 58000, watts: 200, confidence: "estimate", note: "native sm_120 path" },
  { gpu: "GeForce RTX 4080", arch: "Ada sm_89", profile: "16/8/128", nps: 56000, watts: 320, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "GeForce RTX 5070 Ti", arch: "Blackwell sm_120", profile: "16/8/128", nps: 52000, watts: 285, confidence: "profile", note: "avoid batch 256" },
  { gpu: "NVIDIA RTX 5000 Ada", arch: "Ada sm_89", profile: "16/8/128", nps: 50000, watts: 250, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "NVIDIA A100 PCIe", arch: "Ampere sm_80", profile: "12/8/128", nps: 47000, watts: 400, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce RTX 4070 Ti Super", arch: "Ada sm_89", profile: "16/8/128", nps: 47000, watts: 285, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "GeForce RTX 4070 Ti", arch: "Ada sm_89", profile: "16/8/128", nps: 43000, watts: 285, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "GeForce RTX 5070", arch: "Blackwell sm_120", profile: "16/8/128", nps: 40000, watts: 223, confidence: "measured profile", note: "99.9% util measured" },
  { gpu: "GeForce RTX 3090 Ti", arch: "Ampere sm_86", profile: "12/8/128", nps: 39000, watts: 450, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "NVIDIA RTX 4500 Ada", arch: "Ada sm_89", profile: "16/8/128", nps: 38000, watts: 210, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "GeForce RTX 4070 Super", arch: "Ada sm_89", profile: "16/8/128", nps: 37000, watts: 220, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "GeForce RTX 3090", arch: "Ampere sm_86", profile: "12/8/128", nps: 36500, watts: 350, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce RTX 3080 Ti", arch: "Ampere sm_86", profile: "12/8/128", nps: 34000, watts: 350, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "NVIDIA RTX A6000", arch: "Ampere sm_86", profile: "12/8/128", nps: 34000, watts: 300, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "NVIDIA A40", arch: "Ampere sm_86", profile: "12/8/128", nps: 33000, watts: 300, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce RTX 4070", arch: "Ada sm_89", profile: "16/8/128", nps: 32000, watts: 200, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "GeForce RTX 3080", arch: "Ampere sm_86", profile: "12/8/128", nps: 30500, watts: 320, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce RTX 5060 Ti", arch: "Blackwell sm_120", profile: "16/8/128", nps: 28000, watts: 150, confidence: "reference", note: "canonical 28K+ n/s" },
  { gpu: "NVIDIA RTX A5000", arch: "Ampere sm_86", profile: "12/8/128", nps: 27000, watts: 230, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "NVIDIA RTX 4000 Ada", arch: "Ada sm_89", profile: "16/8/128", nps: 26000, watts: 130, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "GeForce RTX 3070 Ti", arch: "Ampere sm_86", profile: "12/8/128", nps: 24000, watts: 290, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce RTX 4060 Ti", arch: "Ada sm_89", profile: "12/8/128", nps: 24000, watts: 164, confidence: "measured profile", note: "100% util measured" },
  { gpu: "GeForce RTX 5060", arch: "Blackwell sm_120", profile: "16/8/128", nps: 22000, watts: 145, confidence: "estimate", note: "native sm_120 path" },
  { gpu: "GeForce RTX 2080 Ti", arch: "Turing sm_75", profile: "12/8/128", nps: 22000, watts: 296, confidence: "measured profile", note: "100% util measured" },
  { gpu: "GeForce RTX 3070", arch: "Ampere sm_86", profile: "12/8/128", nps: 21500, watts: 220, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce RTX 4060 Laptop", arch: "Ada sm_89", profile: "12/8/128", nps: 19000, watts: 115, confidence: "estimate", note: "laptop power varies" },
  { gpu: "GeForce RTX 2080 Super", arch: "Turing sm_75", profile: "12/8/128", nps: 18500, watts: 250, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce RTX 3060 Ti", arch: "Ampere sm_86", profile: "12/8/128", nps: 18000, watts: 190, confidence: "measured profile", note: "100% util measured" },
  { gpu: "GeForce RTX 4060", arch: "Ada sm_89", profile: "12/8/128", nps: 18000, watts: 115, confidence: "estimate", note: "native sm_89 path" },
  { gpu: "GeForce RTX 2080", arch: "Turing sm_75", profile: "12/8/128", nps: 17000, watts: 215, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce RTX 4070 Laptop", arch: "Ada sm_89", profile: "16/8/128", nps: 16500, watts: 115, confidence: "estimate", note: "laptop power varies" },
  { gpu: "GeForce RTX 2070 Super", arch: "Turing sm_75", profile: "12/8/128", nps: 15500, watts: 215, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "NVIDIA RTX A4000", arch: "Ampere sm_86", profile: "12/8/128", nps: 15500, watts: 140, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "NVIDIA L4", arch: "Ada sm_89", profile: "16/8/128", nps: 14500, watts: 72, confidence: "estimate", note: "high efficiency" },
  { gpu: "GeForce RTX 3060", arch: "Ampere sm_86", profile: "12/8/128", nps: 13500, watts: 170, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce RTX 2070", arch: "Turing sm_75", profile: "12/8/128", nps: 13500, watts: 175, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce RTX 2060 Super", arch: "Turing sm_75", profile: "12/8/128", nps: 12500, watts: 175, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce GTX 1080 Ti", arch: "Pascal sm_61", profile: "16/8/128", nps: 12500, watts: 250, confidence: "estimate", note: "native sm_61 path" },
  { gpu: "NVIDIA Titan RTX", arch: "Turing sm_75", profile: "12/8/128", nps: 24000, watts: 280, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce RTX 2060", arch: "Turing sm_75", profile: "12/8/128", nps: 11000, watts: 160, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce RTX 3050", arch: "Ampere sm_86", profile: "12/8/128", nps: 9500, watts: 130, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce GTX 1080", arch: "Pascal sm_61", profile: "16/8/128", nps: 9200, watts: 180, confidence: "estimate", note: "native sm_61 path" },
  { gpu: "GeForce GTX 1660 Ti", arch: "Turing sm_75", profile: "12/8/128", nps: 8200, watts: 120, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce GTX 1070 Ti", arch: "Pascal sm_61", profile: "16/8/128", nps: 8200, watts: 180, confidence: "estimate", note: "native sm_61 path" },
  { gpu: "GeForce GTX 1660 Super", arch: "Turing sm_75", profile: "12/8/128", nps: 7900, watts: 125, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "GeForce GTX 1070", arch: "Pascal sm_61", profile: "16/8/128", nps: 7200, watts: 113, confidence: "measured profile", note: "83% util measured" },
  { gpu: "GeForce GTX 1660", arch: "Turing sm_75", profile: "12/8/128", nps: 7200, watts: 120, confidence: "estimate", note: "PTX JIT path" },
  { gpu: "NVIDIA RTX A2000", arch: "Ampere sm_86", profile: "12/8/128", nps: 7000, watts: 70, confidence: "estimate", note: "efficient small card" },
  { gpu: "GeForce GTX 1050 Ti", arch: "Pascal sm_61", profile: "16/8/128", nps: 2200, watts: 75, confidence: "estimate", note: "entry Pascal" },
  { gpu: "GeForce GTX 980 Ti", arch: "Maxwell sm_52", profile: "16/8/128", nps: 5200, watts: 250, confidence: "smoke test", note: "legacy GPU; verify binary support" },
  { gpu: "GeForce GTX 980", arch: "Maxwell sm_52", profile: "16/8/128", nps: 3900, watts: 165, confidence: "smoke test", note: "legacy GPU; verify binary support" },
  { gpu: "GeForce GTX 970", arch: "Maxwell sm_52", profile: "16/8/128", nps: 3100, watts: 145, confidence: "smoke test", note: "legacy GPU; verify binary support" },
];

function setText(id, value) {
  const element = document.getElementById(id);
  if (element && value !== undefined && value !== null) {
    element.textContent = value;
  }
}

function formatMaybeNumber(value, fallback = "0") {
  const number = Number(value);
  return Number.isFinite(number) ? formatNumber.format(number) : fallback;
}

function formatMaybeHashrate(value, fallback = "Pending") {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? formatHashrate(number) : fallback;
}

function formatHashrate(value) {
  if (!Number.isFinite(value)) return "Unknown";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M n/s`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K n/s`;
  return `${Math.round(value)} n/s`;
}

function formatSatToBtx(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "0.00000000 BTX";
  return `${formatBtx.format(number / 100_000_000)} BTX`;
}

function formatDateTime(value) {
  if (!value) return "No worker yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatFeeBps(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number / 100).toFixed(2)}%` : "0.00%";
}

function formatFeePolicy(policy) {
  const trialDays = Number(policy.trial_days ?? 0);
  const trialBps = Number(policy.trial_fee_bps ?? 0);
  const postTrialBps = Number(policy.post_trial_fee_bps ?? policy.post_trial_pool_fee_bps ?? policy.pool_fee_bps ?? 0);
  if (trialDays > 0 && postTrialBps > trialBps) {
    return `${formatFeeBps(trialBps)} first ${trialDays}d, then ${formatFeeBps(postTrialBps)}`;
  }
  return formatFeeBps(postTrialBps);
}

function formatHourlyUsd(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "Unknown";
  return `${number < 1 ? formatUsdPrecise.format(number) : formatUsdPrice.format(number)}/h`;
}

function formatCostPerBtx(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "Unknown";
  return `${formatUsdPrecise.format(number)}/BTX`;
}

function formatBtxRate(value) {
  if (!Number.isFinite(value)) return "Unknown";
  if (value >= 100) return formatNumber.format(Math.round(value));
  if (value >= 10) return value.toFixed(2);
  if (value >= 1) return value.toFixed(3);
  return value.toFixed(5);
}

function estimateBtxPerHour(nps) {
  if (!Number.isFinite(nps) || !Number.isFinite(currentNetworkHashNps) || currentNetworkHashNps <= 0) {
    return 0;
  }
  const platformFeeMultiplier = Math.max(0, 1 - currentPlatformFeeBps / 10_000);
  return (nps / currentNetworkHashNps) * blockRewardBtx * blocksPerHour * platformFeeMultiplier;
}

function estimatePoolShare(addedHashrateNps) {
  if (!Number.isFinite(addedHashrateNps) || !Number.isFinite(currentNetworkHashNps)) return 0;
  return addedHashrateNps / (currentNetworkHashNps + addedHashrateNps);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeGpuText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\bnvidia\b|\bgeforce\b|\bsxm\b|\bpcie\b|\blaptop\b/g, " ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function gpuModelKey(value) {
  const text = normalizeGpuText(value);
  const specialKeys = [
    "b200", "b100", "h200", "h100", "l40s", "l40", "l4",
    "a100", "a40", "a6000", "a5000", "a4000", "a2000",
    "titan rtx",
  ];
  const special = specialKeys.find((key) => text.includes(key));
  if (special) return special;

  const proMatch = text.match(/\brtx pro\s+(\d{4})\b/);
  if (proMatch) return `rtx pro ${proMatch[1]}`;

  const adaMatch = text.match(/\brtx\s+(\d{4})\s+ada\b/);
  if (adaMatch) return `rtx ${adaMatch[1]} ada`;

  const rtxMatch = text.match(/\brtx\s*(\d{4})(?:\s*(ti|super))?(?:\s*(super))?\b/);
  if (rtxMatch) {
    return [
      "rtx",
      rtxMatch[1],
      rtxMatch[2] || "",
      rtxMatch[3] || "",
    ].filter(Boolean).join(" ");
  }

  const gtxMatch = text.match(/\bgtx\s*(\d{3,4})(?:\s*(ti|super))?\b/);
  if (gtxMatch) {
    return ["gtx", gtxMatch[1], gtxMatch[2] || ""].filter(Boolean).join(" ");
  }

  return text;
}

function findGpuProfileForOffer(offer) {
  const offerKey = gpuModelKey(offer.gpu_name);
  return gpuProfiles.find((profile) => gpuModelKey(profile.gpu) === offerKey)
    || gpuProfiles.find((profile) => {
      const profileText = normalizeGpuText(profile.gpu);
      const offerText = normalizeGpuText(offer.gpu_name);
      return profileText.includes(offerText) || offerText.includes(profileText);
    })
    || null;
}

function enrichVastOffer(offer) {
  const profile = findGpuProfileForOffer(offer);
  const numGpus = Number(offer.num_gpus) || 1;
  const hourly = Number(offer.discounted_dph_total || offer.dph_total);
  const nps = profile ? profile.nps * numGpus : null;
  const btxHour = Number.isFinite(nps) ? estimateBtxPerHour(nps) : null;
  const costPerBtx = Number.isFinite(hourly) && Number.isFinite(btxHour) && btxHour > 0
    ? hourly / btxHour
    : null;

  return {
    ...offer,
    profile,
    numGpus,
    hourly,
    nps,
    btxHour,
    costPerBtx,
  };
}

function buildVastLink(offer) {
  const config = vastReferralConfig || {};
  const base = config.referral_configured ? config.referral_url : config.fallback_url;
  if (!base) return "https://cloud.vast.ai/";

  const replacements = {
    "{offer_id}": offer.id,
    "{ask_contract_id}": offer.ask_contract_id,
    "{gpu_name}": encodeURIComponent(offer.gpu_name || "gpu"),
  };
  let url = String(base);
  Object.entries(replacements).forEach(([token, value]) => {
    url = url.replaceAll(token, value ?? "");
  });

  try {
    const parsed = new URL(url);
    if (config.referral_configured && config.referral_id && !parsed.searchParams.has("ref_id") && !parsed.searchParams.has("ref")) {
      parsed.searchParams.set("ref_id", config.referral_id);
    }
    parsed.searchParams.set("utm_source", "btx_start");
    parsed.searchParams.set("utm_medium", "gpu_rental");
    if (offer.id) parsed.searchParams.set("utm_content", `vast_offer_${offer.id}`);
    return parsed.toString();
  } catch (error) {
    return url;
  }
}

async function hydrateStats() {
  const status = document.getElementById("stats-status");

  try {
    const result = await fetchStatsWithFallback();
    const data = result.data;
    const pool = data.pool || {};
    const health = data.health || {};
    const btxd = health.btxd || {};
    const policy = data.policy || {};

    setText("workers-now", formatMaybeNumber(pool.workers_active_now));
    setText("blocks-24h", formatMaybeNumber(pool.blocks_found_24h));
    const backendFeeBps = Number(policy.post_trial_fee_bps ?? policy.pool_fee_bps ?? 0);
    const backendFee = formatFeePolicy(policy);
    currentNetworkHashNps = Number(pool.network_hash_nps || btxd.network_hash_ps) || currentNetworkHashNps;
    const feeAddress = policy.fee_address || "Pending managed service";
    const treasuryAddress = policy.treasury_address || "Pending managed service";
    setText("backend-live-fee", backendFee);
    setText("backend-policy-fee", backendFee);
    setText("fee-address", feeAddress);
    setText("treasury-address", treasuryAddress);
    setText("backend-fee-address", feeAddress);
    setText("backend-treasury-address", treasuryAddress);
    setText("backend-fee-balance", formatSatToBtx(pool.pending_fee_sat));
    setText("backend-fee-rate", backendFee);
    setText("chain-height", formatMaybeNumber(btxd.blocks));
    setText("workers-24h", formatMaybeNumber(pool.workers_active_24h));
    setText("network-hash", formatMaybeHashrate(pool.network_hash_nps || btxd.network_hash_ps));
    setText("node-peers", formatMaybeNumber(btxd.peers));
    renderGpuRanking();
    renderOperatingModel();

    if (status) {
      const timestamp = data.fetched_at ? new Date(data.fetched_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "recently";
      status.textContent = result.live
        ? `BTX Start stats updated ${timestamp}`
        : `Managed mining service snapshot updated ${timestamp}`;
    }
  } catch (error) {
    if (status) {
      status.textContent = "BTX Start stats unavailable. Mining service is still being connected.";
    }
  }
}

async function fetchStatsWithFallback() {
  const urls = [
    { url: statsUrl, live: true },
    { url: statsFallbackUrl, live: false },
  ];
  let lastError = null;

  for (const candidate of urls) {
    try {
      const response = await fetch(candidate.url, { cache: "no-store" });
      if (!response.ok) throw new Error(`Stats request failed: ${response.status}`);
      return {
        data: await response.json(),
        live: candidate.live,
      };
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("Stats unavailable");
}

async function hydrateTreasuryConfig() {
  try {
    const response = await fetch(treasuryUrl, { cache: "no-store" });
    if (!response.ok) throw new Error(`Treasury request failed: ${response.status}`);
    const treasury = await response.json();
    const targetBps = Number(treasury.post_trial_pool_fee_bps ?? treasury.target_pool_fee_bps ?? 0);
    const feePolicyLabel = formatFeePolicy({
      trial_days: treasury.trial_days,
      trial_fee_bps: treasury.trial_fee_bps,
      post_trial_fee_bps: targetBps,
    });
    const status = treasury.active ? "Connected" : "Preparing";

    currentPlatformFeeBps = targetBps;
    setText("platform-treasury-status", status);
    setText("platform-target-fee", feePolicyLabel);
    setText("platform-fee-hero", feePolicyLabel);
    setText("platform-fee-address", treasury.platform_fee_address || "Pending wallet creation");
    setText("platform-treasury-address", treasury.platform_treasury_address || "Pending wallet creation");
    setText("platform-fee-balance", treasury.platform_fee_balance_btx || "0.00000000 BTX");
    setText("platform-balance-source", treasury.balance_source);
    setText("platform-funds-use", treasury.use_of_funds);
    setText("platform-notice", treasury.notice);
    renderGpuRanking();
    renderOperatingModel();
  } catch (error) {
    setText("platform-treasury-status", "Unavailable");
  }
}

function setupCopyButtons() {
  document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.getElementById(button.dataset.copyTarget);
      if (!target) return;
      const label = button.querySelector("span") || button;
      const originalText = label.textContent;

      try {
        await navigator.clipboard.writeText(target.textContent.trim());
        button.dataset.copied = "true";
        label.textContent = "Copied";
        window.setTimeout(() => {
          button.dataset.copied = "false";
          label.textContent = originalText || "Copy";
        }, 1800);
      } catch (error) {
        label.textContent = "Select";
      }
    });
  });
}

function setupAddressBuilder() {
  const input = document.getElementById("btx-address-input");
  const workerInput = document.getElementById("worker-name-input");
  const command = document.getElementById("install-command");
  const preflightCommand = document.getElementById("preflight-command");
  const localInstallCommand = document.getElementById("local-install-command");
  const localPreflightCommand = document.getElementById("local-preflight-command");
  const macInstallCommand = document.getElementById("mac-install-command");
  const macPreflightCommand = document.getElementById("mac-preflight-command");
  const windowsInstallCommand = document.getElementById("windows-install-command");
  const windowsPreflightCommand = document.getElementById("windows-preflight-command");
  const workerIdCommand = document.getElementById("worker-id-command");
  const walletBalanceCommand = document.getElementById("wallet-balance-command");
  const wrapper = document.querySelector(".address-builder");
  const help = document.getElementById("address-help");
  if (!input || !command || !wrapper || !help) return;
  let dashboardTimer = null;

  function updateCommand() {
    const address = input.value.trim();
    const worker = (workerInput?.value.trim() || "default").replace(/[^a-z0-9._-]/gi, "-");
    const macWorker = worker === "default" ? "mac-ultra" : worker;
    const windowsWorker = worker === "default" ? "windows" : worker;
    const looksValid = /^btx1z[a-z0-9]{20,}$/i.test(address);
    const addressForCommand = looksValid ? address : placeholderAddress;
    const addressFlag = looksValid ? ` --address '${address}'` : "";

    command.textContent = `curl -fsSL ${installerUrl} | bash -s -- --address '${addressForCommand}' --worker '${worker}'`;
    if (localInstallCommand) {
      localInstallCommand.textContent = `curl -fsSL ${installerUrl} | bash -s -- --address '${addressForCommand}' --worker '${worker}'`;
    }
    if (preflightCommand) {
      preflightCommand.textContent = `curl -fsSL ${installerUrl} | bash -s -- --preflight${addressFlag} --worker '${worker}'`;
      if (localPreflightCommand) {
        localPreflightCommand.textContent = preflightCommand.textContent;
      }
    }
    if (macInstallCommand) {
      macInstallCommand.textContent = `curl -fsSL ${installerUrl} | bash -s -- --address '${addressForCommand}' --worker '${macWorker}' --solver-backend metal --local-solver "$HOME/.dexbtx-miner/bin/btx-gbt-solve" --trust-local-solver`;
    }
    if (macPreflightCommand) {
      macPreflightCommand.textContent = `curl -fsSL ${installerUrl} | bash -s -- --preflight${addressFlag} --solver-backend metal --local-solver "$HOME/.dexbtx-miner/bin/btx-gbt-solve" --trust-local-solver --worker '${macWorker}'`;
    }
    if (windowsInstallCommand) {
      windowsInstallCommand.textContent = `curl -fsSL ${installerUrl} | bash -s -- --address '${addressForCommand}' --worker '${windowsWorker}'`;
    }
    if (windowsPreflightCommand) {
      windowsPreflightCommand.textContent = `curl -fsSL ${installerUrl} | bash -s -- --preflight${addressFlag} --worker '${windowsWorker}'`;
    }
    const balanceAddress = looksValid ? address : "btx1z...your_address";
    const workerId = `${balanceAddress}.${worker}`;
    if (workerIdCommand) workerIdCommand.textContent = workerId;
    if (walletBalanceCommand) walletBalanceCommand.textContent = looksValid
      ? `Check wallet balance for ${address}`
      : "Check the wallet that owns your BTX address";
    wrapper.dataset.valid = address ? String(looksValid) : "";
    if (!address) {
      help.textContent = "The command mines to this address. Do not use someone else's address.";
    } else if (looksValid) {
      help.textContent = "Command updated. Shares and payouts will be credited to this address.";
    } else {
      help.textContent = "This does not look like a BTX address yet. The command still uses the placeholder.";
    }

    if (dashboardTimer) window.clearTimeout(dashboardTimer);
    dashboardTimer = window.setTimeout(() => {
      hydratePersonalDashboard(looksValid ? address : "");
    }, 350);
  }

  input.addEventListener("input", updateCommand);
  workerInput?.addEventListener("input", updateCommand);
  updateCommand();
}

async function hydratePersonalDashboard(address = null) {
  const input = document.getElementById("btx-address-input");
  const payoutAddress = address ?? input?.value.trim() ?? "";
  const looksValid = /^btx1z[a-z0-9]{20,}$/i.test(payoutAddress);
  const help = document.getElementById("dashboard-help");
  const status = document.getElementById("dashboard-status");
  const workers = document.getElementById("dashboard-workers");
  const shares = document.getElementById("dashboard-shares");
  const balance = document.getElementById("dashboard-balance");
  const fees = document.getElementById("dashboard-fees");
  const lastSeen = document.getElementById("dashboard-last-seen");
  const workerList = document.getElementById("dashboard-worker-list");
  if (!status || !workers || !shares || !balance || !fees || !lastSeen || !workerList) return;

  if (!payoutAddress) {
    status.textContent = "Waiting for address";
    workers.textContent = "0";
    shares.textContent = "0";
    balance.textContent = "0.00000000 BTX";
    fees.textContent = "0.00000000 BTX";
    lastSeen.textContent = "No worker yet";
    workerList.textContent = "No workers are attached to this address yet.";
    if (help) help.textContent = "Paste your BTX address above. The dashboard uses only your payout address, never private keys.";
    return;
  }

  if (!looksValid) {
    status.textContent = "Invalid address";
    workerList.textContent = "Enter a valid BTX address to load a personal dashboard.";
    if (help) help.textContent = "This address does not look valid yet.";
    return;
  }

  status.textContent = "Loading";
  if (help) help.textContent = "Loading pool-side dashboard data for this payout address.";
  try {
    const response = await fetch(`${dashboardBaseUrl}/${encodeURIComponent(payoutAddress)}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`dashboard ${response.status}`);
    const dashboard = await response.json();
    const dashboardWorkers = Array.isArray(dashboard.workers) ? dashboard.workers : [];
    const accepted = Number(dashboard.shares?.accepted) || 0;
    const accepted24h = Number(dashboard.shares?.accepted_24h) || 0;
    const rejected = Number(dashboard.shares?.rejected) || 0;
    const balanceData = dashboard.balance || {};
    const latestWorker = dashboardWorkers[0];

    status.textContent = dashboard.known ? "Found" : "No worker yet";
    workers.textContent = formatMaybeNumber(dashboardWorkers.length);
    shares.textContent = accepted24h > 0
      ? `${formatMaybeNumber(accepted24h)} / 24h`
      : formatMaybeNumber(accepted);
    balance.textContent = formatSatToBtx(balanceData.payable_sat || 0);
    fees.textContent = formatSatToBtx(balanceData.fee_sat || 0);
    lastSeen.textContent = latestWorker ? formatDateTime(latestWorker.last_seen_at) : "No worker yet";

    if (!dashboard.known) {
      workerList.textContent = "This address is not in the pool database yet. It will appear here after the first worker connects.";
      if (help) help.textContent = "Dashboard ready. No worker has connected with this payout address yet.";
      return;
    }

    if (!dashboardWorkers.length) {
      workerList.textContent = "Address found, but no worker is currently attached.";
    } else {
      workerList.innerHTML = dashboardWorkers.map((worker) => `
        <div>
          <strong>${escapeHtml(worker.worker_name || "default")}</strong>
          <span>${escapeHtml(formatDateTime(worker.last_seen_at))}</span>
        </div>
      `).join("");
    }
    if (help) {
      help.textContent = rejected > 0
        ? `${formatMaybeNumber(rejected)} rejected shares are recorded. Once validation is live, accepted shares and pending payout update here.`
        : "Dashboard ready. Accepted shares, workers, pending payout, and fee state update here.";
    }
  } catch (error) {
    status.textContent = "Unavailable";
    workerList.textContent = "Dashboard API is not reachable right now. Try refresh again shortly.";
    if (help) help.textContent = "Could not load the dashboard API.";
  }
}

function setupPersonalDashboard() {
  document.getElementById("dashboard-refresh")?.addEventListener("click", () => {
    hydratePersonalDashboard();
  });
  hydratePersonalDashboard();
}

function renderGpuRanking() {
  const body = document.getElementById("gpu-ranking-body");
  if (!body) return;

  const search = document.getElementById("gpu-search")?.value.trim().toLowerCase() || "";
  const sort = document.getElementById("gpu-sort")?.value || "yield";
  const filtered = gpuProfiles
    .map((profile) => {
      const btxHour = estimateBtxPerHour(profile.nps);
      return {
        ...profile,
        btxHour,
        btxDay: btxHour * 24,
        efficiency: profile.nps / profile.watts,
      };
    })
    .filter((profile) => {
      const haystack = `${profile.gpu} ${profile.arch} ${profile.profile} ${profile.confidence} ${profile.note}`.toLowerCase();
      return haystack.includes(search);
    })
    .sort((left, right) => {
      if (sort === "efficiency") return right.efficiency - left.efficiency;
      if (sort === "speed") return right.nps - left.nps;
      if (sort === "name") return left.gpu.localeCompare(right.gpu);
      return right.btxHour - left.btxHour;
    });

  body.innerHTML = filtered.length
    ? filtered.map((profile, index) => `
        <tr>
          <td>${index + 1}</td>
          <td>
            <strong>${escapeHtml(profile.gpu)}</strong>
            <span>${escapeHtml(profile.arch)}</span>
          </td>
          <td>${escapeHtml(profile.profile)}</td>
          <td>${formatHashrate(profile.nps)}</td>
          <td>${formatBtxRate(profile.btxHour)}</td>
          <td>${formatBtxRate(profile.btxDay)}</td>
          <td>${profile.efficiency.toFixed(1)} n/s/W</td>
          <td><span class="confidence">${escapeHtml(profile.confidence)}</span><small>${escapeHtml(profile.note)}</small></td>
        </tr>
      `).join("")
    : `<tr><td colspan="8">No GPU matched this search.</td></tr>`;

  setText("gpu-ranking-count", `${filtered.length} GPUs shown`);
  setText("gpu-network-reference", formatHashrate(currentNetworkHashNps));
  setText("gpu-block-reward", `${blockRewardBtx} BTX`);
  setText("profile-btx-hour", `${formatBtxRate(estimateBtxPerHour(28_000))} BTX/h`);
}

function setupGpuRanking() {
  document.getElementById("gpu-search")?.addEventListener("input", renderGpuRanking);
  document.getElementById("gpu-sort")?.addEventListener("change", renderGpuRanking);
  renderGpuRanking();
}

async function hydrateVastOffers() {
  const status = document.getElementById("vast-status");
  try {
    const [offersResponse, referralResponse] = await Promise.all([
      fetch(vastOffersUrl, { cache: "no-store" }),
      fetch(vastReferralUrl, { cache: "no-store" }),
    ]);
    if (!offersResponse.ok) throw new Error(`Vast offers request failed: ${offersResponse.status}`);
    if (!referralResponse.ok) throw new Error(`Vast referral config failed: ${referralResponse.status}`);

    const offersPayload = await offersResponse.json();
    vastReferralConfig = await referralResponse.json();
    vastOffers = Array.isArray(offersPayload.offers) ? offersPayload.offers : [];

    const timestamp = offersPayload.fetched_at
      ? new Date(offersPayload.fetched_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : "recently";
    if (status) status.textContent = `Vast pricing snapshot updated ${timestamp}`;
    const referralStatus = vastReferralConfig.referral_configured
      ? `Active: ref ${vastReferralConfig.referral_id || "configured"}`
      : "Needs link";
    setText("vast-referral-status", referralStatus);
    setText("vast-disclosure", vastReferralConfig.disclosure);
    renderVastOffers();
  } catch (error) {
    if (status) status.textContent = "Vast pricing unavailable. Check the latest Vast marketplace directly.";
  }
}

function renderVastOffers() {
  const body = document.getElementById("vast-offers-body");
  if (!body) return;

  const search = document.getElementById("vast-search")?.value.trim().toLowerCase() || "";
  const sort = document.getElementById("vast-sort")?.value || "cost";
  const enriched = vastOffers
    .map(enrichVastOffer)
    .filter((offer) => {
      const haystack = `${offer.gpu_name} ${offer.geolocation} ${offer.driver_version} ${offer.verification}`.toLowerCase();
      return haystack.includes(search);
    })
    .sort((left, right) => {
      if (sort === "price") return left.hourly - right.hourly;
      if (sort === "yield") return (right.btxHour || 0) - (left.btxHour || 0);
      if (sort === "reliability") return (right.reliability2 || 0) - (left.reliability2 || 0);
      return (left.costPerBtx ?? Number.POSITIVE_INFINITY) - (right.costPerBtx ?? Number.POSITIVE_INFINITY);
    });

  const bestByCost = enriched.find((offer) => Number.isFinite(offer.costPerBtx));
  const cheapest = enriched.find((offer) => Number.isFinite(offer.hourly));
  const bestYield = enriched.find((offer) => Number.isFinite(offer.btxHour));

  setText("vast-offer-count", `${formatNumber.format(enriched.length)} offers`);
  setText("vast-best-price", cheapest ? formatHourlyUsd(cheapest.hourly) : "Pending");
  setText("vast-best-cost", bestByCost ? formatCostPerBtx(bestByCost.costPerBtx) : "Pending");
  setText("vast-best-yield", bestYield ? `${formatBtxRate(bestYield.btxHour)} BTX/h` : "Pending");

  body.innerHTML = enriched.length
    ? enriched.slice(0, 24).map((offer, index) => {
      const reliability = Number.isFinite(offer.reliability2)
        ? `${(offer.reliability2 * 100).toFixed(1)}%`
        : "Unknown";
      const vramGb = Number.isFinite(offer.gpu_ram_mb)
        ? `${Math.round(offer.gpu_ram_mb / 1024)}GB`
        : "VRAM n/a";
      const linkLabel = vastReferralConfig?.referral_configured ? "Rent via Vast" : "Open Vast";

      return `
        <tr>
          <td>${index + 1}</td>
          <td>
            <strong>${escapeHtml(offer.gpu_name || "Vast GPU")}</strong>
            <span>${offer.numGpus} GPU · ${vramGb}</span>
          </td>
          <td>${formatHourlyUsd(offer.hourly)}</td>
          <td>${Number.isFinite(offer.btxHour) ? `${formatBtxRate(offer.btxHour)} BTX` : "Profile needed"}</td>
          <td>${Number.isFinite(offer.costPerBtx) ? formatCostPerBtx(offer.costPerBtx) : "Unknown"}</td>
          <td>${escapeHtml(offer.geolocation || "Unknown")}</td>
          <td>${reliability}</td>
          <td>
            <a class="mini-link" href="${escapeHtml(buildVastLink(offer))}" target="_blank" rel="noreferrer">${linkLabel}</a>
          </td>
        </tr>
      `;
    }).join("")
    : `<tr><td colspan="8">No Vast offers matched this search.</td></tr>`;
}

function setupVastOffers() {
  document.getElementById("vast-search")?.addEventListener("input", renderVastOffers);
  document.getElementById("vast-sort")?.addEventListener("change", renderVastOffers);
  hydrateVastOffers();
}

function renderOperatingModel() {
  const body = document.getElementById("operating-model-body");
  if (!body) return;

  const scenarioMiners = [100, 300, 500];
  const referenceGpuNps = 28_000;
  const dailyEmissionBtx = blockRewardBtx * blocksPerDay;

  body.innerHTML = scenarioMiners.map((miners) => {
    const addedHashrate = miners * referenceGpuNps;
    const share = estimatePoolShare(addedHashrate);
    const grossBtxDay = dailyEmissionBtx * share;
    const feeCells = [0, 50, 100].map((feeBps) => {
      const feeBtx = grossBtxDay * (feeBps / 10_000);
      return `
        <td>
          <strong>${formatBtxRate(feeBtx)} BTX</strong>
          <span>${formatUsd.format(feeBtx * btxModelPriceUsd)} / day</span>
        </td>
      `;
    }).join("");

    return `
      <tr>
        <td>
          <strong>${formatNumber.format(miners)} miners</strong>
          <span>5060 Ti-class at 28K n/s</span>
        </td>
        <td>${formatHashrate(addedHashrate)}</td>
        <td>${(share * 100).toFixed(1)}%</td>
        <td>${formatBtxRate(grossBtxDay)} BTX</td>
        ${feeCells}
      </tr>
    `;
  }).join("");

  setText("operating-price", formatUsdPrice.format(btxModelPriceUsd));
  setText("operating-network", formatHashrate(currentNetworkHashNps));
}

function setupHeroCanvas() {
  const canvas = document.getElementById("hero-canvas");
  if (!canvas) return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const context = canvas.getContext("2d");
  let width = 0;
  let height = 0;
  let particles = [];
  let rafId = null;

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    width = Math.max(1, Math.floor(rect.width));
    height = Math.max(1, Math.floor(rect.height));
    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);

    const count = Math.max(28, Math.min(82, Math.floor(width / 18)));
    particles = Array.from({ length: count }, (_, index) => ({
      x: (index * 97) % width,
      y: (index * 53) % height,
      vx: ((index % 7) - 3) * 0.05,
      vy: 0.18 + (index % 5) * 0.035,
      size: 1.2 + (index % 4) * 0.45,
      pulse: index / count,
    }));
  }

  function drawGrid() {
    context.clearRect(0, 0, width, height);
    context.fillStyle = "#0b0f14";
    context.fillRect(0, 0, width, height);

    context.strokeStyle = "rgba(52, 211, 200, 0.06)";
    context.lineWidth = 1;
    for (let x = 0; x < width; x += 44) {
      context.beginPath();
      context.moveTo(x, 0);
      context.lineTo(x, height);
      context.stroke();
    }
    for (let y = 0; y < height; y += 44) {
      context.beginPath();
      context.moveTo(0, y);
      context.lineTo(width, y);
      context.stroke();
    }
  }

  function draw(time = 0) {
    drawGrid();

    const centerX = width * 0.68;
    const centerY = height * 0.46;

    particles.forEach((particle, index) => {
      if (!reduceMotion) {
        particle.x += particle.vx;
        particle.y += particle.vy;
        if (particle.y > height + 20) particle.y = -20;
        if (particle.x < -20) particle.x = width + 20;
        if (particle.x > width + 20) particle.x = -20;
      }

      const dx = particle.x - centerX;
      const dy = particle.y - centerY;
      const distance = Math.hypot(dx, dy);
      if (distance < 210 && index % 3 === 0) {
        context.strokeStyle = `rgba(255, 123, 0, ${0.16 - distance / 1600})`;
        context.beginPath();
        context.moveTo(particle.x, particle.y);
        context.lineTo(centerX, centerY);
        context.stroke();
      }

      const pulse = reduceMotion ? 0.35 : 0.35 + Math.sin(time / 600 + particle.pulse * 6.28) * 0.28;
      context.fillStyle = index % 5 === 0
        ? `rgba(255, 123, 0, ${0.45 + pulse})`
        : `rgba(52, 211, 200, ${0.3 + pulse})`;
      context.beginPath();
      context.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
      context.fill();
    });

    context.fillStyle = "rgba(255, 123, 0, 0.14)";
    context.beginPath();
    context.arc(centerX, centerY, 92, 0, Math.PI * 2);
    context.fill();
    context.strokeStyle = "rgba(255, 123, 0, 0.58)";
    context.lineWidth = 2;
    context.strokeRect(centerX - 54, centerY - 54, 108, 108);
    context.strokeStyle = "rgba(52, 211, 200, 0.38)";
    context.strokeRect(centerX - 36, centerY - 36, 72, 72);

    if (!reduceMotion) {
      rafId = window.requestAnimationFrame(draw);
    }
  }

  resize();
  draw();

  window.addEventListener("resize", () => {
    if (rafId) window.cancelAnimationFrame(rafId);
    resize();
    draw();
  });
}

setupHeroCanvas();
setupCopyButtons();
setupAddressBuilder();
setupPersonalDashboard();
setupGpuRanking();
setupVastOffers();
renderOperatingModel();
hydrateStats();
hydrateTreasuryConfig();
