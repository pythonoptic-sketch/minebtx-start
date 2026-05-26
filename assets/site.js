const siteBaseUrl = "https://drinknile.com";
const installerUrl = `${siteBaseUrl}/install.sh`;
const statsUrl = "stats-snapshot.json";
const treasuryUrl = "platform-treasury.json";
const placeholderAddress = "btx1z...YOUR_BTX_ADDRESS...";
const blockRewardBtx = 20;
const targetBlockSeconds = 90;
const blocksPerHour = 3600 / targetBlockSeconds;
const blocksPerDay = 86400 / targetBlockSeconds;
const btxModelPriceUsd = 5.707747399717103;
const referenceNetworkHashNps = 2_338_067;
let currentNetworkHashNps = referenceNetworkHashNps;
let currentPlatformFeeBps = 0;

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

function formatHashrate(value) {
  if (!Number.isFinite(value)) return "Unknown";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M n/s`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K n/s`;
  return `${Math.round(value)} n/s`;
}

function formatSatToBtx(value) {
  if (!Number.isFinite(value)) return "Unknown";
  return `${formatBtx.format(value / 100_000_000)} BTX`;
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

async function hydrateStats() {
  const status = document.getElementById("stats-status");

  try {
    const response = await fetch(statsUrl, { cache: "no-store" });
    if (!response.ok) throw new Error(`Stats request failed: ${response.status}`);

    const data = await response.json();
    const pool = data.pool || {};
    const health = data.health || {};
    const btxd = health.btxd || {};
    const policy = data.policy || {};

    setText("workers-now", formatNumber.format(pool.workers_active_now));
    setText("blocks-24h", formatNumber.format(pool.blocks_found_24h));
    const backendFeeBps = Number(policy.pool_fee_bps ?? 250);
    const backendFee = `${(backendFeeBps / 100).toFixed(2)}%`;
    currentNetworkHashNps = Number(pool.network_hash_nps || btxd.network_hash_ps) || currentNetworkHashNps;
    setText("backend-live-fee", backendFee);
    setText("backend-policy-fee", backendFee);
    setText("fee-address", policy.fee_address);
    setText("treasury-address", policy.treasury_address);
    setText("backend-fee-address", policy.fee_address);
    setText("backend-treasury-address", policy.treasury_address);
    setText("backend-fee-balance", formatSatToBtx(pool.pending_fee_sat));
    setText("backend-fee-rate", backendFee);
    setText("chain-height", formatNumber.format(btxd.blocks));
    setText("workers-24h", formatNumber.format(pool.workers_active_24h));
    setText("network-hash", formatHashrate(pool.network_hash_nps || btxd.network_hash_ps));
    setText("node-peers", formatNumber.format(btxd.peers));
    renderGpuRanking();
    renderOperatingModel();

    if (status) {
      const timestamp = data.fetched_at ? new Date(data.fetched_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "recently";
      status.textContent = `Stats snapshot updated ${timestamp}`;
    }
  } catch (error) {
    if (status) {
      status.textContent = "Live stats unavailable, showing latest bundled snapshot.";
    }
  }
}

async function hydrateTreasuryConfig() {
  try {
    const response = await fetch(treasuryUrl, { cache: "no-store" });
    if (!response.ok) throw new Error(`Treasury request failed: ${response.status}`);
    const treasury = await response.json();
    const targetBps = Number(treasury.target_pool_fee_bps ?? 0);
    const status = treasury.active ? "Connected" : "Pending";

    currentPlatformFeeBps = targetBps;
    setText("platform-treasury-status", status);
    setText("platform-target-fee", `${(targetBps / 100).toFixed(2)}%`);
    setText("platform-fee-hero", `${(targetBps / 100).toFixed(2)}%`);
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
  const workerIdCommand = document.getElementById("worker-id-command");
  const walletBalanceCommand = document.getElementById("wallet-balance-command");
  const wrapper = document.querySelector(".address-builder");
  const help = document.getElementById("address-help");
  if (!input || !command || !wrapper || !help) return;

  function updateCommand() {
    const address = input.value.trim();
    const worker = (workerInput?.value.trim() || "default").replace(/[^a-z0-9._-]/gi, "-");
    const looksValid = /^btx1z[a-z0-9]{20,}$/i.test(address);
    const addressForCommand = looksValid ? address : placeholderAddress;

    command.textContent = `curl -fsSL ${installerUrl} | bash -s -- --address '${addressForCommand}' --worker '${worker}'`;
    if (preflightCommand) {
      const addressFlag = looksValid ? ` --address '${address}'` : "";
      preflightCommand.textContent = `curl -fsSL ${installerUrl} | bash -s -- --preflight${addressFlag} --worker '${worker}'`;
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
  }

  input.addEventListener("input", updateCommand);
  workerInput?.addEventListener("input", updateCommand);
  updateCommand();
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
setupGpuRanking();
renderOperatingModel();
hydrateStats();
hydrateTreasuryConfig();
