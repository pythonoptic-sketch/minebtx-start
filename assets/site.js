const siteBaseUrl = "https://pythonoptic-sketch.github.io/minebtx-start";
const installerUrl = `${siteBaseUrl}/install.sh`;
const statsUrl = "stats-snapshot.json";
const placeholderAddress = "btx1z...YOUR_BTX_ADDRESS...";

const formatNumber = new Intl.NumberFormat("en-US");

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
    setText("pool-fee", `${((policy.pool_fee_bps || 250) / 100).toFixed(2)}%`);
    setText("fee-address", policy.fee_address);
    setText("treasury-address", policy.treasury_address);
    setText("chain-height", formatNumber.format(btxd.blocks));
    setText("workers-24h", formatNumber.format(pool.workers_active_24h));
    setText("network-hash", formatHashrate(pool.network_hash_nps || btxd.network_hash_ps));
    setText("node-peers", formatNumber.format(btxd.peers));

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
  const telegramCommand = document.getElementById("telegram-command");
  const balanceCommand = document.getElementById("balance-command");
  const blockCommand = document.getElementById("block-command");
  const workerIdCommand = document.getElementById("worker-id-command");
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
    if (telegramCommand) {
      const balanceAddress = looksValid ? address : "btx1z...your_address";
      const workerId = `${balanceAddress}.${worker}`;
      telegramCommand.textContent = `/mybalance ${workerId}`;
      if (balanceCommand) balanceCommand.textContent = `/mybalance ${workerId}`;
      if (blockCommand) blockCommand.textContent = `/myblock ${workerId}`;
      if (workerIdCommand) workerIdCommand.textContent = workerId;
    }
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
hydrateStats();
