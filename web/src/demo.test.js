import test from 'node:test';
import assert from 'node:assert/strict';
import { incidents, filterIncidents } from './demo.js';

test('search finds the affected road and direction without case sensitivity', () => {
  assert.deepEqual(filterIncidents(incidents, ' KENNEDY ', { incident: true, construction: true }).map((item) => item.id), ['demo-401']);
  assert.equal(filterIncidents(incidents, 'northbound', { incident: true }).length, 1);
});

test('disabled layers are excluded even if they match the search', () => {
  assert.equal(filterIncidents(incidents, 'Gardiner', { incident: true, construction: false }).length, 0);
  assert.equal(filterIncidents(incidents, '', { incident: false, construction: false }).length, 0);
});

test('unknown roads produce an empty result without changing the input', () => {
  const before = structuredClone(incidents);
  assert.deepEqual(filterIncidents(incidents, 'unknown road', { incident: true, construction: true }), []);
  assert.deepEqual(incidents, before);
});

test('search covers cities outside Toronto and northern Ontario', () => {
  const layers = { incident: true, construction: true };
  assert.deepEqual(filterIncidents(incidents, ' OTTAWA ', layers).map((item) => item.id), ['demo-ottawa']);
  assert.deepEqual(filterIncidents(incidents, 'thunder bay', layers).map((item) => item.id), ['demo-thunder-bay']);
  assert.deepEqual(filterIncidents(incidents, 'london', layers).map((item) => item.id), ['demo-london']);
});
