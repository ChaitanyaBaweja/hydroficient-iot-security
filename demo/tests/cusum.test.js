const test = require('node:test');
const assert = require('node:assert');
const { Rng } = require('../src/prng.js');
const M = require('../src/model.js');
const { Cusum } = require('../src/cusum.js');

test('stays pinned near zero on a normal day', () => {
  const rng = new Rng(1337);
  const c = new Cusum();
  let peak = 0, alarmed = false;
  for (let i = 0; i < 45; i++) {
    alarmed = c.update(M.normalPressure(rng)) || alarmed;
    peak = Math.max(peak, c.S);
  }
  assert.ok(!alarmed, 'must not false-alarm on the recorded normal day');
  assert.ok(peak < 5, `peak S was ${peak}, expected well under the threshold`);
});

test('false alarm rate on normal days is under 0.1 percent', () => {
  const rng = new Rng(99);
  let alarms = 0;
  const DAYS = 5000;
  for (let d = 0; d < DAYS; d++) {
    const c = new Cusum();
    for (let i = 0; i < 45; i++) if (c.update(M.normalPressure(rng))) { alarms++; break; }
  }
  assert.ok(alarms / DAYS < 0.001, `rate was ${alarms / DAYS}`);
});

test('detects the patient attack with at least 11 minutes of margin', () => {
  // Spec guarantee: margin median 16, never below 11, over 20k days.
  const rng = new Rng(1337);
  let worstMargin = Infinity;
  for (let d = 0; d < 2000; d++) {
    const c = new Cusum();
    let gate = 45, alarm = null, damage = null;
    const win = [];
    for (let t = 1; t <= 400; t++) {
      const x = M.attackPressure(rng);
      if (c.update(x) && alarm === null) alarm = t;
      win.push(x);
      gate = M.controllerStep(gate, win.slice(-M.P.WINDOW));
      if (damage === null && M.residual(gate) <= M.P.SPRINKLER_MIN) damage = t;
      if (alarm !== null && damage !== null) break;
    }
    assert.ok(alarm !== null && damage !== null, 'both events must occur');
    worstMargin = Math.min(worstMargin, damage - alarm);
  }
  assert.ok(worstMargin >= 11, `worst margin was ${worstMargin}, spec floor is 11`);
});

test('raising slack past the damage floor lets the attacker win', () => {
  // This is the Artifact 3 view 2 interactive. Verify the effect is real.
  const outcome = (k) => {
    const rng = new Rng(4);
    const c = new Cusum(60, k, 10);
    let gate = 45, alarm = null, damage = null;
    const win = [];
    for (let t = 1; t <= 400; t++) {
      const x = rng.uniform(60.3, 61.7); // bias 1.0
      if (c.update(x) && alarm === null) alarm = t;
      win.push(x);
      gate = M.controllerStep(gate, win.slice(-M.P.WINDOW));
      if (damage === null && M.residual(gate) <= M.P.SPRINKLER_MIN) damage = t;
    }
    return { alarm, damage };
  };
  const tight = outcome(0.5), loose = outcome(0.9);
  assert.ok(tight.alarm < tight.damage, 'slack 0.5: defender should win');
  assert.ok(loose.alarm > loose.damage, 'slack 0.9: attacker should win');
});
