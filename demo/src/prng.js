// Deterministic PRNG. Verified to produce a byte-identical stream to
// tools/reference.py, which is what makes golden-vector testing possible.
function mulberry32(a) {
  return function () {
    a |= 0;
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

class Rng {
  constructor(seed = 1337) {
    this.next = mulberry32(seed);
    this._spare = null;
  }
  uniform(lo, hi) {
    return lo + this.next() * (hi - lo);
  }
  // Box-Muller. The spare value is cached so the draw order stays deterministic.
  normal(mu = 0, sigma = 1) {
    if (this._spare !== null) {
      const s = this._spare;
      this._spare = null;
      return mu + sigma * s;
    }
    let u = 0, v = 0;
    while (u === 0) u = this.next();
    while (v === 0) v = this.next();
    const mag = Math.sqrt(-2 * Math.log(u));
    this._spare = mag * Math.sin(2 * Math.PI * v);
    return mu + sigma * mag * Math.cos(2 * Math.PI * v);
  }
}

const api = { mulberry32, Rng };
if (typeof module !== 'undefined' && module.exports) module.exports = api;
if (typeof window !== 'undefined') window.Demo = Object.assign(window.Demo || {}, api);
