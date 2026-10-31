import type { ScanResult } from './types';

// Partition the selected shelf's identities, not photo observations or tasks.
// Deduplication and matched-first precedence keep repeated readings from inflating totals.
export function summarizeShelf(scan: Pick<ScanResult, 'planogram_items' | 'shelf_items'>) {
  const assigned = new Set(scan.planogram_items.map(item => item.sku));
  const matched = new Set<string>();
  const possible = new Set<string>();
  for (const item of scan.shelf_items) {
    if (!item.sku || !assigned.has(item.sku)) continue;
    if (item.status === 'matched') matched.add(item.sku);
    else if (item.catalogue_status === 'matched') possible.add(item.sku);
  }
  for (const sku of matched) possible.delete(sku);
  return {
    expected: assigned.size,
    matched: matched.size,
    possible: possible.size,
    unidentified: assigned.size - matched.size - possible.size,
  };
}
