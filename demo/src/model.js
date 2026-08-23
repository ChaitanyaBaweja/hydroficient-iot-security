// Simulation model for the Grand Marina demo.
// Every constant here is fixed by docs/plans/2026-08-23-tech-demo-design.md.
const P = {
  MU0: 60.0, SIGMA: 1.0, P_LO: 58.0, P_HI: 62.0,
  F_BASE: 50.0, F_SLOPE: 2.5, F_NOISE: 1.5, F_LO: 45.0, F_HI: 55.0,
  GATE0: 45.0, GATE_MIN: 5.0, GATE_MAX: 100.0,
  KP: 0.9, WINDOW: 10, DEADBAND: 0.8, RESTORE: 0.02,
  ATTACK_LO: 60.5, ATTACK_HI: 61.9,
  CRUDE_PRESSURE: 85.0, CRUDE_FLOW: 50.0,
  SPRINKLER_MIN: 20.0, FLOORS: 12,
};

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

const normalPressure = (rng) => clamp(rng.normal(P.MU0, P.SIGMA), P.P_LO, P.P_HI);
const attackPressure = (rng) => rng.uniform(P.ATTACK_LO, P.ATTACK_HI);

// Flow is correlated with the *reported* pressure, which is what makes the
// Artifact 1 scatter plot a tilted ellipse rather than a round cloud.
const reportedFlow = (rng, pressure) =>
  clamp(P.F_BASE + P.F_SLOPE * (pressure - P.MU0) + rng.normal(0, P.F_NOISE), P.F_LO, P.F_HI);

// Cloud-side conservation controller. Both the drive and the restoring term are
// required: a pure integrator random-walks the gate out of band on a normal day.
function controllerStep(gate, window) {
  let e = window.reduce((s, x) => s + x, 0) / window.length - P.MU0;
  if (Math.abs(e) < P.DEADBAND) e = 0;
  return clamp(gate - P.KP * e + P.RESTORE * (P.GATE0 - gate), P.GATE_MIN, P.GATE_MAX);
}

// Linearised hydraulics — a demo simplification, not engineering.
const residual = (gate) => gate * 1.0;
const trueFlow = (gate) => P.F_BASE * (gate / P.GATE0);
const darkFloors = (res) => clamp(P.FLOORS - Math.floor(res / 2), 0, P.FLOORS);

const api = { P, clamp, normalPressure, attackPressure, reportedFlow,
              controllerStep, residual, trueFlow, darkFloors };
if (typeof module !== 'undefined' && module.exports) module.exports = api;
if (typeof window !== 'undefined') window.Demo = Object.assign(window.Demo || {}, api);
