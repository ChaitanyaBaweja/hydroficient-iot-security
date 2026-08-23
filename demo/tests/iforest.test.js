const test = require('node:test');
const assert = require('node:assert');
const { Rng } = require('../src/prng.js');
const M = require('../src/model.js');
const { IsolationForest, pathLengthFor } = require('../src/iforest.js');

function normalData(n = 1000, seed = 1337) {
  const rng = new Rng(seed);
  return Array.from({ length: n }, () => {
    const p = M.normalPressure(rng);
    return [p, M.reportedFlow(rng, p)];
  });
}

test('scores an obvious outlier higher than an interior point', () => {
  const f = new IsolationForest({ trees: 100, seed: 1337 }).fit(normalData());
  assert.ok(f.score([85, 50]) > f.score([60, 50]), 'crude attack must score higher');
});

test('isolates the outlier in far fewer cuts than an interior point', () => {
  // This asymmetry is the entire teaching point of Artifact 1.
  const data = normalData();
  const rng = new Rng(1337);
  const f = new IsolationForest({ trees: 100, seed: 1337 }).fit(data);
  const outlier = f.avgPathLength([85, 50]);
  const interior = f.avgPathLength([60, 50]);
  // Measured: outlier ~6.5 cuts vs interior ~12.2. Assert the gap, not an exact ratio.
  assert.ok(outlier < interior * 0.7, `outlier ${outlier} vs interior ${interior}`);
});

test('flags the crude attack and clears the patient attack', () => {
  const data = normalData();
  const f = new IsolationForest({ trees: 100, seed: 1337 }).fit(data);
  const threshold = f.percentileThreshold(data, 0.99);

  assert.ok(f.score([85, 50]) > threshold, 'crude 85 PSI must be flagged');

  // Patient attack: in-band pressure with matched flow. Must NOT be flagged.
  const rng = new Rng(7);
  let flagged = 0;
  for (let i = 0; i < 200; i++) {
    const p = M.attackPressure(rng);
    if (f.score([p, M.fabricatedFlow(rng, p)]) > threshold) flagged++;
  }
  assert.ok(flagged / 200 < 0.05, `patient attack flagged ${flagged}/200, must stay green`);
});

// Regression guard. The whole demo rests on a 45-minute patient run in which not one
// reading trips the fence. Fabricating flow at the real sensor's spread leaves roughly
// 1 run in 80 dirty, which would break that claim live and unrecoverably. The tighter
// fabrication spread must keep every run of every seed clean.
test('no patient run trips the fence, across many seeds', () => {
  const data = normalData();
  const f = new IsolationForest({ trees: 100, seed: 1337 }).fit(data);
  const threshold = f.percentileThreshold(data, 0.999);

  let dirtyRuns = 0;
  for (let seed = 1; seed <= 300; seed++) {
    const rng = new Rng(seed);
    for (let minute = 0; minute < 45; minute++) {
      const p = M.attackPressure(rng);
      if (f.score([p, M.fabricatedFlow(rng, p)]) > threshold) { dirtyRuns++; break; }
    }
  }
  assert.strictEqual(dirtyRuns, 0, `${dirtyRuns}/300 patient runs raised an alert`);
});

test('is deterministic for a fixed seed', () => {
  const data = normalData();
  const a = new IsolationForest({ trees: 50, seed: 3 }).fit(data);
  const b = new IsolationForest({ trees: 50, seed: 3 }).fit(data);
  assert.strictEqual(a.score([61, 52]), b.score([61, 52]));
});
