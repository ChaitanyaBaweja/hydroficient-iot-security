// Shared canvas drawing helpers. Deliberately minimal — no chart library, because
// the page must be self-contained and CSP forbids external scripts.
const PALETTE = {
  bg: '#0d1117', grid: '#21262d', text: '#c9d1d9', muted: '#6e7681',
  normal: '#3fb950', warn: '#d29922', danger: '#f85149', accent: '#58a6ff',
};

function scaler(domain, range) {
  const [d0, d1] = domain, [r0, r1] = range;
  return (v) => r0 + ((v - d0) / (d1 - d0)) * (r1 - r0);
}

function axes(ctx, box, xDomain, yDomain, xLabel, yLabel) {
  const { x, y, w, h } = box;
  ctx.strokeStyle = PALETTE.grid; ctx.fillStyle = PALETTE.muted;
  ctx.lineWidth = 1; ctx.font = '12px system-ui, sans-serif';
  ctx.strokeRect(x, y, w, h);
  ctx.fillText(xLabel, x + w / 2 - 30, y + h + 32);
  ctx.save(); ctx.translate(x - 40, y + h / 2); ctx.rotate(-Math.PI / 2);
  ctx.fillText(yLabel, -20, 0); ctx.restore();
}

function scatter(ctx, box, pts, xDomain, yDomain, colour, radius = 1.6) {
  const sx = scaler(xDomain, [box.x, box.x + box.w]);
  const sy = scaler(yDomain, [box.y + box.h, box.y]);
  ctx.fillStyle = colour;
  for (const [px, py] of pts) {
    ctx.beginPath(); ctx.arc(sx(px), sy(py), radius, 0, Math.PI * 2); ctx.fill();
  }
}

function polyline(ctx, box, series, xDomain, yDomain, colour, width = 2) {
  const sx = scaler(xDomain, [box.x, box.x + box.w]);
  const sy = scaler(yDomain, [box.y + box.h, box.y]);
  ctx.strokeStyle = colour; ctx.lineWidth = width; ctx.beginPath();
  series.forEach(([px, py], i) => (i ? ctx.lineTo(sx(px), sy(py)) : ctx.moveTo(sx(px), sy(py))));
  ctx.stroke();
}

const api = { PALETTE, scaler, axes, scatter, polyline };
if (typeof module !== 'undefined' && module.exports) module.exports = api;
if (typeof window !== 'undefined') window.Demo = Object.assign(window.Demo || {}, api);
