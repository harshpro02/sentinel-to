import test from 'node:test';
import assert from 'node:assert/strict';
import { categories, categoryMatches, itemMatches } from './categories.js';

test('category search finds useful stops and all categories have distinct routes', () => {
  assert.equal(new Set(categories.map((item) => item.id)).size, 15);
  assert.ok(categories.filter((item) => categoryMatches(item, 'rest areas')).some((item) => item.id === 'rest-areas'));
  assert.ok(categories.filter((item) => categoryMatches(item, 'fuel')).some((item) => item.id === 'service-centres'));
});

test('place search includes practical facts without changing source records', () => {
  const item = { road: 'King City', location: 'Highway 400', facts: [{ label: 'Amenities', value: 'Washrooms and WiFi' }] };
  assert.equal(itemMatches(item, 'wifi'), true);
  assert.equal(itemMatches(item, 'HIGHWAY 400'), true);
  assert.equal(itemMatches(item, 'ferry'), false);
  assert.equal(item.facts[0].value, 'Washrooms and WiFi');
});
