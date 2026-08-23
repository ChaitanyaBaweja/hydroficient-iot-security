const test = require('node:test');
const assert = require('node:assert');
const { mulberry32, Rng } = require('../src/prng.js');

// Golden values produced by tools/reference.py (Python) — must match exactly.
const GOLDEN_1337 = [
  0.184411832597, 0.189989251317, 0.810471992241,
  0.643748822156, 0.430774615612, 0.381045897026,
];

test('mulberry32 matches the Python reference stream for seed 1337', () => {
  const r = mulberry32(1337);
  for (const expected of GOLDEN_1337) {
    assert.strictEqual(Number(r().toFixed(12)), expected);
  }
});

test('same seed reproduces the same stream', () => {
  const a = mulberry32(42), b = mulberry32(42);
  for (let i = 0; i < 50; i++) assert.strictEqual(a(), b());
});

test('normal() is centred near mu with roughly sigma spread', () => {
  const rng = new Rng(1337);
  const xs = Array.from({ length: 20000 }, () => rng.normal(60, 1));
  const mean = xs.reduce((s, x) => s + x, 0) / xs.length;
  const sd = Math.sqrt(xs.reduce((s, x) => s + (x - mean) ** 2, 0) / xs.length);
  assert.ok(Math.abs(mean - 60) < 0.05, `mean was ${mean}`);
  assert.ok(Math.abs(sd - 1) < 0.05, `sd was ${sd}`);
});

test('uniform(lo, hi) never leaves its bounds', () => {
  const rng = new Rng(7);
  for (let i = 0; i < 10000; i++) {
    const v = rng.uniform(60.5, 61.9);
    assert.ok(v >= 60.5 && v < 61.9);
  }
});
