/**
 * Network Cascade Lab — Frontend Application Logic
 * ==================================================
 *
 * This connects to the Flask API and handles:
 *   - Loading network info on startup
 *   - Running simulations with user-specified parameters
 *   - Drawing charts (cascade over time, threshold sweep)
 *   - Updating the results panel and activity log
 */

const API_BASE = 'http://localhost:5000/api';

// ─── State ─────────────────────────────────────────────────

let networkInfo = null;
let lastSimResult = null;
let lastSweepResult = null;

// ─── Initialize ────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Set up slider event listeners
    setupSliders();

    // Load network info
    loadNetworkInfo();
});

function setupSliders() {
    const thresholdSlider = document.getElementById('threshold-slider');
    const thresholdValue = document.getElementById('threshold-value');
    thresholdSlider.addEventListener('input', () => {
        thresholdValue.textContent = parseFloat(thresholdSlider.value).toFixed(2);
    });

    const homophilySlider = document.getElementById('homophily-slider');
    const homophilyValue = document.getElementById('homophily-value');
    homophilySlider.addEventListener('input', () => {
        homophilyValue.textContent = parseFloat(homophilySlider.value).toFixed(2);
    });
}

// ─── API ───────────────────────────────────────────────────

async function fetchAPI(endpoint, method = 'GET', body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(`${API_BASE}${endpoint}`, opts);
    if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
    return res.json();
}

async function loadNetworkInfo() {
    try {
        networkInfo = await fetchAPI('/network-info');

        document.getElementById('info-nodes').textContent = networkInfo.n_nodes;
        document.getElementById('info-edges').textContent = networkInfo.n_edges.toLocaleString();
        document.getElementById('info-density').textContent = networkInfo.density;
        document.getElementById('info-degree').textContent = networkInfo.avg_degree;
        document.getElementById('info-departments').textContent =
            Object.entries(networkInfo.departments)
                .map(([d, c]) => `${d} (${c})`)
                .join(', ');

        setConnectionStatus('connected', 'API Connected');
        addLog('success', `Connected! Network: ${networkInfo.n_nodes} nodes, ${networkInfo.n_edges.toLocaleString()} edges`);
    } catch (err) {
        setConnectionStatus('error', 'API Offline');
        addLog('error', `Cannot connect to API at ${API_BASE}. Start the server: python src/api.py`);
        console.error(err);
    }
}

function setConnectionStatus(status, text) {
    const dot = document.querySelector('.status-dot');
    const label = document.querySelector('.status-text');
    dot.className = `status-dot ${status}`;
    label.textContent = text;
}

// ─── Simulation ────────────────────────────────────────────

async function runSimulation() {
    const btn = document.getElementById('btn-simulate');
    btn.classList.add('loading');
    btn.querySelector('.btn-icon').textContent = '⏳';

    const params = getParams();

    addLog('info', `Running simulation: θ=${params.threshold}, seeds=${params.n_seeds}, ` +
                   `strategy=${params.seed_strategy}, homophily=${params.homophily_weight}`);

    try {
        lastSimResult = await fetchAPI('/simulate', 'POST', params);

        updateResultsSummary(lastSimResult);
        drawCascadeChart(lastSimResult);

        addLog('success', `Cascade complete: ${lastSimResult.adoption_fraction}% adoption ` +
                         `(${lastSimResult.n_adopted}/${lastSimResult.n_total} nodes, ` +
                         `${lastSimResult.converged_at} steps)`);
    } catch (err) {
        addLog('error', `Simulation failed: ${err.message}`);
    } finally {
        btn.classList.remove('loading');
        btn.querySelector('.btn-icon').textContent = '▶';
    }
}

async function runThresholdSweep() {
    const btn = document.getElementById('btn-sweep');
    btn.classList.add('loading');
    btn.querySelector('.btn-icon').textContent = '⏳';

    const params = getParams();
    const sweepParams = {
        n_seeds: params.n_seeds,
        homophily_weight: params.homophily_weight,
        n_runs: 5,
        thresholds: [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.8],
    };

    addLog('info', `Running threshold sweep: ${sweepParams.thresholds.length} thresholds × ${sweepParams.n_runs} runs...`);

    try {
        lastSweepResult = await fetchAPI('/threshold-sweep', 'POST', sweepParams);

        drawSweepChart(lastSweepResult);

        addLog('success', `Sweep complete! ${sweepParams.thresholds.length} thresholds tested.`);

        // Find critical threshold
        const critIdx = findCriticalThreshold(lastSweepResult);
        if (critIdx >= 0) {
            addLog('data', `⚡ Phase transition near θ=${lastSweepResult.thresholds[critIdx]}`);
        }
    } catch (err) {
        addLog('error', `Sweep failed: ${err.message}`);
    } finally {
        btn.classList.remove('loading');
        btn.querySelector('.btn-icon').textContent = '📊';
    }
}

function getParams() {
    return {
        threshold: parseFloat(document.getElementById('threshold-slider').value),
        n_seeds: parseInt(document.getElementById('seeds-input').value),
        seed_strategy: document.getElementById('seed-strategy').value,
        homophily_weight: parseFloat(document.getElementById('homophily-slider').value),
    };
}

// ─── Results Panel ─────────────────────────────────────────

function updateResultsSummary(result) {
    const summary = document.getElementById('results-summary');
    summary.classList.remove('hidden');

    document.getElementById('result-adoption').textContent = `${result.adoption_fraction}%`;
    document.getElementById('result-adopted').textContent = `${result.n_adopted}/${result.n_total}`;
    document.getElementById('result-steps').textContent = result.converged_at;
    document.getElementById('result-threshold').textContent = `θ = ${result.threshold}`;

    const verdict = document.getElementById('result-verdict');
    if (result.adoption_fraction > 50) {
        verdict.className = 'result-verdict success';
        verdict.innerHTML = `✅ <strong>Cascade succeeded!</strong> The idea spread to ${result.adoption_fraction}% of the network. ` +
                           `At threshold θ=${result.threshold}, peer pressure was sufficient to drive mass adoption.`;
    } else if (result.adoption_fraction > 15) {
        verdict.className = 'result-verdict partial';
        verdict.innerHTML = `⚠️ <strong>Partial cascade.</strong> The idea reached ${result.adoption_fraction}% — ` +
                           `it spread to some clusters but couldn't break through to the whole network.`;
    } else {
        verdict.className = 'result-verdict failure';
        verdict.innerHTML = `❌ <strong>Cascade failed.</strong> Only ${result.adoption_fraction}% adopted. ` +
                           `The threshold θ=${result.threshold} was too high for the cascade to sustain itself beyond the initial seeds.`;
    }
}

// ─── Charts (Canvas-based, no dependencies) ────────────────

function drawCascadeChart(result) {
    const canvas = document.getElementById('cascade-chart');
    const ctx = canvas.getContext('2d');
    const placeholder = document.getElementById('cascade-placeholder');
    placeholder.classList.add('hidden');

    // Ensure crisp drawing
    const rect = canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    const W = rect.width;
    const H = rect.height;

    ctx.clearRect(0, 0, W, H);

    const data = result.steps_adoption_pct;
    if (data.length < 2) {
        drawTextCenter(ctx, W, H, 'Cascade converged immediately (1 step)');
        return;
    }

    const pad = { top: 30, right: 30, bottom: 50, left: 60 };
    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    const xScale = (i) => pad.left + (i / (data.length - 1)) * plotW;
    const yScale = (v) => pad.top + plotH - (v / 100) * plotH;

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 1;
    for (let y = 0; y <= 100; y += 20) {
        ctx.beginPath();
        ctx.moveTo(pad.left, yScale(y));
        ctx.lineTo(W - pad.right, yScale(y));
        ctx.stroke();
        ctx.fillStyle = '#6b7280';
        ctx.font = '11px Inter';
        ctx.textAlign = 'right';
        ctx.fillText(`${y}%`, pad.left - 8, yScale(y) + 4);
    }

    // Fill gradient
    const gradient = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
    gradient.addColorStop(0, 'rgba(74, 222, 128, 0.25)');
    gradient.addColorStop(1, 'rgba(74, 222, 128, 0.01)');

    ctx.beginPath();
    ctx.moveTo(xScale(0), yScale(0));
    data.forEach((v, i) => ctx.lineTo(xScale(i), yScale(v)));
    ctx.lineTo(xScale(data.length - 1), yScale(0));
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Line
    ctx.beginPath();
    data.forEach((v, i) => {
        if (i === 0) ctx.moveTo(xScale(i), yScale(v));
        else ctx.lineTo(xScale(i), yScale(v));
    });
    ctx.strokeStyle = '#4ade80';
    ctx.lineWidth = 2.5;
    ctx.lineJoin = 'round';
    ctx.stroke();

    // Points
    data.forEach((v, i) => {
        ctx.beginPath();
        ctx.arc(xScale(i), yScale(v), 4, 0, Math.PI * 2);
        ctx.fillStyle = '#0f1117';
        ctx.fill();
        ctx.strokeStyle = '#4ade80';
        ctx.lineWidth = 2;
        ctx.stroke();
    });

    // X-axis labels
    ctx.fillStyle = '#6b7280';
    ctx.font = '11px Inter';
    ctx.textAlign = 'center';
    const step = Math.max(1, Math.floor(data.length / 10));
    for (let i = 0; i < data.length; i += step) {
        ctx.fillText(`${i}`, xScale(i), H - pad.bottom + 20);
    }

    // Axis titles
    ctx.fillStyle = '#9aa0b2';
    ctx.font = 'bold 12px Inter';
    ctx.textAlign = 'center';
    ctx.fillText('Simulation Step', W / 2, H - 8);

    ctx.save();
    ctx.translate(14, H / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Adoption (%)', 0, 0);
    ctx.restore();
}

function drawSweepChart(result) {
    const canvas = document.getElementById('sweep-chart');
    const ctx = canvas.getContext('2d');
    const placeholder = document.getElementById('sweep-placeholder');
    placeholder.classList.add('hidden');

    const rect = canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    const W = rect.width;
    const H = rect.height;

    ctx.clearRect(0, 0, W, H);

    const thresholds = result.thresholds;
    const means = result.mean_adoption;
    const stds = result.std_adoption;

    if (thresholds.length < 2) return;

    const pad = { top: 30, right: 30, bottom: 50, left: 60 };
    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    const tMin = Math.min(...thresholds);
    const tMax = Math.max(...thresholds);

    const xScale = (t) => pad.left + ((t - tMin) / (tMax - tMin)) * plotW;
    const yScale = (v) => pad.top + plotH - (v / 100) * plotH;

    // Grid
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 1;
    for (let y = 0; y <= 100; y += 20) {
        ctx.beginPath();
        ctx.moveTo(pad.left, yScale(y));
        ctx.lineTo(W - pad.right, yScale(y));
        ctx.stroke();
        ctx.fillStyle = '#6b7280';
        ctx.font = '11px Inter';
        ctx.textAlign = 'right';
        ctx.fillText(`${y}%`, pad.left - 8, yScale(y) + 4);
    }

    // Error band (std)
    ctx.beginPath();
    thresholds.forEach((t, i) => {
        const x = xScale(t);
        const yTop = yScale(Math.min(100, means[i] + stds[i]));
        if (i === 0) ctx.moveTo(x, yTop);
        else ctx.lineTo(x, yTop);
    });
    for (let i = thresholds.length - 1; i >= 0; i--) {
        const x = xScale(thresholds[i]);
        const yBot = yScale(Math.max(0, means[i] - stds[i]));
        ctx.lineTo(x, yBot);
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(96, 165, 250, 0.12)';
    ctx.fill();

    // Line
    ctx.beginPath();
    thresholds.forEach((t, i) => {
        const x = xScale(t);
        const y = yScale(means[i]);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#60a5fa';
    ctx.lineWidth = 2.5;
    ctx.lineJoin = 'round';
    ctx.stroke();

    // Points + error bars
    thresholds.forEach((t, i) => {
        const x = xScale(t);
        const y = yScale(means[i]);

        // Error bar
        ctx.beginPath();
        ctx.moveTo(x, yScale(Math.min(100, means[i] + stds[i])));
        ctx.lineTo(x, yScale(Math.max(0, means[i] - stds[i])));
        ctx.strokeStyle = 'rgba(96, 165, 250, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Point
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#0f1117';
        ctx.fill();
        ctx.strokeStyle = '#60a5fa';
        ctx.lineWidth = 2;
        ctx.stroke();
    });

    // X-axis labels
    ctx.fillStyle = '#6b7280';
    ctx.font = '11px Inter';
    ctx.textAlign = 'center';
    thresholds.forEach((t) => {
        ctx.fillText(t.toFixed(2), xScale(t), H - pad.bottom + 20);
    });

    // Axis titles
    ctx.fillStyle = '#9aa0b2';
    ctx.font = 'bold 12px Inter';
    ctx.textAlign = 'center';
    ctx.fillText('Adoption Threshold (θ)', W / 2, H - 8);

    ctx.save();
    ctx.translate(14, H / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Adoption (%)', 0, 0);
    ctx.restore();

    // Critical threshold annotation
    const critIdx = findCriticalThreshold(result);
    if (critIdx >= 0) {
        const cx = xScale(thresholds[critIdx]);
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(cx, pad.top);
        ctx.lineTo(cx, pad.top + plotH);
        ctx.strokeStyle = 'rgba(248, 113, 113, 0.5)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = '#f87171';
        ctx.font = 'bold 11px Inter';
        ctx.textAlign = 'left';
        ctx.fillText(`Critical θ ≈ ${thresholds[critIdx]}`, cx + 6, pad.top + 16);
    }
}

function findCriticalThreshold(result) {
    const means = result.mean_adoption;
    let maxDrop = 0;
    let maxIdx = -1;
    for (let i = 1; i < means.length; i++) {
        const drop = means[i - 1] - means[i];
        if (drop > maxDrop) {
            maxDrop = drop;
            maxIdx = i;
        }
    }
    return maxDrop > 5 ? maxIdx : -1;  // Only mark if drop > 5%
}

function drawTextCenter(ctx, W, H, text) {
    ctx.fillStyle = '#6b7280';
    ctx.font = '13px Inter';
    ctx.textAlign = 'center';
    ctx.fillText(text, W / 2, H / 2);
}

// ─── Activity Log ──────────────────────────────────────────

function addLog(type, message) {
    const container = document.getElementById('log-container');
    const entry = document.createElement('div');
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    entry.className = `log-entry log-${type}`;
    entry.innerHTML = `<span style="opacity:0.5">[${time}]</span> ${message}`;
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;

    // Keep max 50 entries
    while (container.children.length > 50) {
        container.removeChild(container.firstChild);
    }
}
