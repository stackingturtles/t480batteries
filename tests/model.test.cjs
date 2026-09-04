const test = require('node:test');
const assert = require('node:assert/strict');
const M = require('../Model.js');

test('zero cycles/percentage/power remain visible; missing values stay unknown', () => {
  assert.equal(M.percent(0), '0%');
  assert.equal(M.quantity(0, 'W'), '0W');
  assert.equal(M.quantity(null, 'Wh'), '—');
  assert.equal(M.percent(undefined), '—');
});
test('per-battery estimates, thresholds and standby are explicit', () => {
  assert.equal(M.duration(7260, true), '~2h 1m');
  assert.equal(M.duration(null, true), '—');
  assert.equal(M.threshold({thresholdStart: 75, thresholdEnd: 80}), '75–80%');
  assert.equal(M.status({state: 'standby'}), 'Standby');
  assert.notEqual(M.icon({state:'standby', percentage:80}), M.icon({state:'charging', percentage:80}));
});
test('missing packs and invalid percentages do not paint a charged battery', () => {
  assert.equal(M.fraction(null), 0);
  assert.equal(M.fraction(200), 1);
  assert.equal(M.icon({state:'absent'}), M.icon({percentage: NaN}));
});
test('stock profile navigation remains bounded', () => {
  assert.equal(M.selectProfileIndex(0, -1, ['balanced']), 0);
  assert.equal(M.selectProfileIndex(0, 1, ['balanced','performance']), 1);
  assert.deepEqual(M.parseProfiles('balanced\t1\nperformance\t0\n', 0).profiles, ['balanced','performance']);
});

test('saver reflects both hardware limits and helper availability', () => {
  const packs = [{present: true, thresholdStart: 75, thresholdEnd: 80}, {present: true, thresholdStart: 75, thresholdEnd: 80}];
  assert.equal(M.saverState({batteries: packs, chargeControlInstalled: true}).enabled, true);
  packs[1].thresholdEnd = 100;
  assert.equal(M.saverState({batteries: packs, chargeControlInstalled: true}).enabled, false);
  assert.equal(M.saverState({batteries: packs}).available, false);
  assert.equal(M.saverState({batteries: []}).enabled, false);
});
