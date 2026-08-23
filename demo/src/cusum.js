// One-sided CUSUM on the raw reported reading (NOT the controller's rolling mean —
// that convention shifts the alarm by several minutes).
//
// The slack k and the zero floor are what pin S near zero on a normal day. A plain
// cumulative sum of (x - mu0) is a random walk that diverges as sqrt(n) and would
// break the Artifact 3 view 1 beat entirely.
class Cusum {
  constructor(mu0 = 60.0, k = 0.5, h = 10.0) {
    Object.assign(this, { mu0, k, h, S: 0 });
  }
  update(x) {
    this.S = Math.max(0, this.S + (x - this.mu0 - this.k));
    return this.S >= this.h;
  }
  reset() { this.S = 0; }
}

const api = { Cusum };
if (typeof module !== 'undefined' && module.exports) module.exports = api;
if (typeof window !== 'undefined') window.Demo = Object.assign(window.Demo || {}, api);
