const test = require('node:test');
const assert = require('node:assert');
const { Rng } = require('../src/prng.js');
const M = require('../src/model.js');

test('normal pressure never leaves the 58-62 band', () => {
  const rng = new Rng(1337);
  for (let i = 0; i < 20000; i++) {
    const p = M.normalPressure(rng);
    assert.ok(p >= 58 && p <= 62, `got ${p}`);
  }
});

test('attack pressure never leaves the normal band either', () => {
  const rng = new Rng(1337);
  let max = -Infinity;
  for (let i = 0; i < 20000; i++) {
    const p = M.attackPressure(rng);
    assert.ok(p >= 58 && p <= 62, `got ${p}`);
    max = Math.max(max, p);
  }
  assert.ok(max < 61.9, `attack max ${max} should stay under 61.9`);
});

test('reported flow spans 45-55 with mean near 50', () => {
  const rng = new Rng(1337);
  const fs = [];
  for (let i = 0; i < 20000; i++) fs.push(M.reportedFlow(rng, M.normalPressure(rng)));
  const mean = fs.reduce((s, x) => s + x, 0) / fs.length;
  assert.ok(Math.min(...fs) >= 45 && Math.max(...fs) <= 55);
  assert.ok(Math.abs(mean - 50) < 0.5, `mean ${mean}`);
});

test('controller holds the gate at 45 when pressure is on target', () => {
  let gate = 45;
  const win = Array(10).fill(60.0);
  for (let i = 0; i < 100; i++) gate = M.controllerStep(gate, win);
  assert.ok(Math.abs(gate - 45) < 0.01, `gate drifted to ${gate}`);
});

// The deadband (0.8) — not the analytic fixed point (0.556) — is the real damage
// floor, because it binds first. These two tests pin that down.
test('sustained bias below the deadband never moves the gate', () => {
  for (const e of [0.5, 0.7, 0.79]) {
    let gate = 45;
    const win = Array(10).fill(60.0 + e);
    for (let i = 0; i < 5000; i++) gate = M.controllerStep(gate, win);
    assert.strictEqual(Math.round(gate * 1e6) / 1e6, 45, `bias ${e} moved the gate to ${gate}`);
  }
});

test('sustained bias above the deadband drives the gate past the damage line', () => {
  for (const e of [0.81, 0.9, 1.2]) {
    let gate = 45;
    const win = Array(10).fill(60.0 + e);
    for (let i = 0; i < 5000; i++) gate = M.controllerStep(gate, win);
    assert.ok(gate <= 20, `bias ${e} only reached ${gate}`);
  }
});

test('deadband suppresses small errors entirely', () => {
  let gate = 45;
  const win = Array(10).fill(60.5); // e = 0.5, inside the 0.8 deadband
  for (let i = 0; i < 500; i++) gate = M.controllerStep(gate, win);
  assert.strictEqual(Math.round(gate * 1e6) / 1e6, 45);
});

test('hydraulics: residual tracks gate and floors darken top-down', () => {
  assert.strictEqual(M.residual(45), 45);
  assert.strictEqual(M.darkFloors(45), 0);
  assert.strictEqual(M.darkFloors(23.9), 1);   // floor 12 only
  assert.strictEqual(M.darkFloors(11.2), 7);   // floors 6-12
  assert.ok(M.trueFlow(11.2) < 20, 'true flow must collapse out of the 45-55 band');
});
