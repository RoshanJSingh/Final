import assert from 'node:assert/strict';
import { test } from 'node:test';
import { summarizeShelf } from '../app/src/analysisSummary.ts';
const planogram_items = ['a', 'b', 'c'].map(sku => ({ sku }));
test('selected shelf totals partition matched, possible and unidentified titles', () => {
  assert.deepEqual(summarizeShelf({ planogram_items, shelf_items: [
    { sku: 'a', status: 'matched', catalogue_status: 'matched' },
    { sku: 'b', status: 'needs_review', catalogue_status: 'matched' },
    { sku: 'elsewhere', status: 'misplaced', catalogue_status: 'matched' },
    { status: 'unexpected' },
  ] }), { expected: 3, matched: 1, possible: 1, unidentified: 1 });
});
test('duplicates cannot inflate totals and accepted matches take precedence', () => {
  assert.deepEqual(summarizeShelf({ planogram_items: [...planogram_items, { sku: 'a' }], shelf_items: [
    { sku: 'a', status: 'needs_review', catalogue_status: 'matched' },
    { sku: 'a', status: 'matched' }, { sku: 'a', status: 'matched' },
  ] }), { expected: 3, matched: 1, possible: 0, unidentified: 2 });
});
test('empty catalogue never implies 100 percent recognition', () => {
  assert.deepEqual(summarizeShelf({ planogram_items: [], shelf_items: [] }), { expected: 0, matched: 0, possible: 0, unidentified: 0 });
});
test('100 of 110 single-pass matches leaves 10 unidentified', () => {
  assert.deepEqual(summarizeShelf({
    planogram_items: Array.from({ length: 110 }, (_, i) => ({ sku: String(i) })),
    shelf_items: Array.from({ length: 100 }, (_, i) => ({ sku: String(i), status: 'matched', title_status: 'single_read' })),
  }), { expected: 110, matched: 100, possible: 0, unidentified: 10 });
});
