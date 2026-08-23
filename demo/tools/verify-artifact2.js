/**
 * Headless acceptance check for dist/2-grand-marina.html.
 *
 * Lifts the SIM-CORE block straight out of the *built* page and replays it under
 * Node, so what is verified here is the code that will actually run on stage — not
 * a re-implementation of it. Canvas rendering and layout are not covered; those
 * have to be checked by eye at 1920x1080.
 *
 * Run: node tools/verify-artifact2.js
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PAGE = path.join(ROOT, 'dist', '2-grand-marina.html');

// The src modules self-register onto window.Demo, exactly as they do in the browser.
global.window = {};
require(path.join(ROOT, 'src', 'prng.js'));
require(path.join(ROOT, 'src', 'model.js'));
require(path.join(ROOT, 'src', 'iforest.js'));
require(path.join(ROOT, 'src', 'ui.js'));
const D = global.window.Demo;

const html = fs.readFileSync(PAGE, 'utf8');
const block = html.match(/\/\/ ==== SIM-CORE-BEGIN ====([\s\S]*?)\/\/ ==== SIM-CORE-END ====/);
if (!block) {
  console.error('FAIL: could not find the SIM-CORE block in dist/2-grand-marina.html');
  process.exit(1);
}
const SIM = new Function('window', block[1] + '\nreturn SIM;')(global.window);

let failures = 0;
function check(label, ok, detail) {
  if (!ok) failures++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}`);
  if (detail) console.log(`        ${detail}`);
}

console.log('AI fence threshold (99.9th pct of 1,000 normal readings):', SIM.threshold.toFixed(5));
console.log('');

// ---------------------------------------------------------------- criterion 1
const crude = SIM.run('crude');
const crudeLive = crude.frames.slice(1);
console.log('--- CRUDE ATTACK ---');
console.log(`  reported 85.0 PSI / 50.0 LPM, score ${crudeLive[0].score.toFixed(4)} vs fence ${SIM.threshold.toFixed(4)}`);
check('1a. AI flags every crude reading',
  crudeLive.every((f) => !f.checks.ai),
  `${crudeLive.filter((f) => !f.checks.ai).length}/${crudeLive.length} readings flagged`);
check('1b. no crude reading is forwarded to the controller',
  crudeLive.every((f) => !f.accepted));
check('1c. gate is still exactly 45% at the end of the crude run',
  crude.finalGate === D.P.GATE0,
  `final gate ${crude.finalGate.toFixed(6)}%, residual ${crude.finalResidual.toFixed(2)} PSI, dark floors ${crude.finalDark}`);
check('1d. the other four checks stay honest (they really do pass)',
  crudeLive.every((f) => f.checks.mtls && f.checks.hmac && f.checks.timestamp && f.checks.sequence));

// ---------------------------------------------------------------- criteria 2 and 3
const patient = SIM.run('patient', SIM.DEFAULT_BIAS);
const live = patient.frames.slice(1);
console.log('');
console.log('--- PATIENT ATTACK (bias +1.2 PSI) ---');
live.forEach((f) => {
  console.log(
    `  min ${String(f.t).padStart(2, '0')}  reported ${f.reportedPressure.toFixed(3)} PSI` +
    `  flow ${f.reportedFlow.toFixed(2)} LPM` +
    `  in-band ${f.reportedPressure >= 58 && f.reportedPressure <= 62 ? 'YES' : 'NO '}` +
    `  score ${f.score.toFixed(4)}` +
    `  checks ${['mtls', 'hmac', 'timestamp', 'sequence', 'ai'].every((k) => f.checks[k]) ? 'ALL PASS' : 'FAIL    '}` +
    `  gate ${f.gate.toFixed(2)}%  residual ${f.residual.toFixed(2)} PSI  dark ${f.dark}`);
});

const readings = live.map((f) => f.reportedPressure);
check('2a. all five checks stay green for the whole patient run',
  live.every((f) => f.checks.mtls && f.checks.hmac && f.checks.timestamp && f.checks.sequence && f.checks.ai),
  `alerts raised: ${patient.alerts}`);
check('2b. zero readings fall outside 58-62',
  patient.outOfBand === 0,
  `min ${Math.min(...readings).toFixed(3)}, max ${Math.max(...readings).toFixed(3)}, out-of-band count ${patient.outOfBand}`);
check('3a. sprinkler residual ends below 20 PSI',
  patient.finalResidual < D.P.SPRINKLER_MIN,
  `final residual ${patient.finalResidual.toFixed(2)} PSI, gate ${patient.finalGate.toFixed(2)}%, ` +
  `true flow ${patient.finalTrueFlow.toFixed(2)} LPM, dark floors ${patient.finalDark}`);
check('3b. the impaired state is reached during the run and never recovers',
  patient.impairedAt !== null && live.slice(patient.impairedAt - 1).every((f) => f.impaired),
  `first crossed the 20 PSI line at minute ${patient.impairedAt} of ${SIM.RUN_MINUTES}`);
check('3c. floors darken top-down as the residual falls',
  live.every((f, i) => i === 0 || f.dark >= live[i - 1].dark || f.residual > live[i - 1].residual),
  `final dark floors: ${patient.finalDark} of ${D.P.FLOORS}`);

// ---------------------------------------------------------------- the interlock
console.log('');
console.log('--- CONTROL INTERLOCK ---');
check('4a. every accepted reading, and only accepted readings, move the gate',
  crude.frames.every((f) => f.accepted || f.gate === D.P.GATE0));

// ---------------------------------------------------------------- bias slider sweep
console.log('');
console.log('--- BIAS SLIDER SWEEP (the "what if they went slower?" question) ---');
for (let b = 0; b <= 2.5001; b += 0.1) {
  const bias = Math.round(b * 10) / 10;
  const r = SIM.run('patient', bias);
  const l = r.frames.slice(1);
  const green = l.every((f) => f.checks.ai);
  console.log(
    `  bias +${bias.toFixed(1)}  outOfBand ${r.outOfBand}  alerts ${String(r.alerts).padStart(2)}` +
    `  allGreen ${green ? 'YES' : 'NO '}  finalGate ${r.finalGate.toFixed(2)}%` +
    `  finalResidual ${r.finalResidual.toFixed(2)} PSI  ${r.finalResidual < 20 ? 'IMPAIRED' : 'safe'}`);
  if (r.outOfBand !== 0) failures++;
}

console.log('');
console.log(failures === 0 ? 'ALL ACCEPTANCE CHECKS PASSED' : `${failures} CHECK(S) FAILED`);
process.exit(failures === 0 ? 0 : 1);
