import { useRetail } from '../demoContext';
import type { ScanResult } from '../types';
import { summarizeShelf } from '../analysisSummary';

export function ResultsSummary({ scan }: { scan: ScanResult }) {
  const retail = useRetail();
  const counts = summarizeShelf(scan);
  const rows = [
    { label: 'Matched', value: counts.matched, description: 'Names read in your photo that match this shelf’s list.', tone: 'text-emerald-800 bg-emerald-50 border-emerald-200' },
    { label: 'Possible matches', value: counts.possible, description: 'Names linked to the list, but still needing confirmation.', tone: 'text-amber-900 bg-amber-50 border-amber-200' },
    { label: 'Not identified', value: counts.unidentified, description: 'Names on the list that we could not identify. They may be hidden or unreadable.', tone: 'text-slate-800 bg-slate-50 border-slate-200' },
  ];
  return <section aria-label={retail ? 'Shelf product summary' : 'Shelf title summary'} className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 mb-5">
    <div className="flex flex-wrap items-start justify-between gap-3 mb-4"><div><h2 className="text-lg font-bold text-slate-900">Your shelf results</h2><p className="text-sm text-slate-600 mt-1">{counts.expected ? <>Compared with <strong>{counts.expected} {retail ? 'catalogue products' : 'book titles'}</strong> assigned to {scan.bay_code}.</> : retail ? 'No products are assigned to this shelf.' : 'No book titles are assigned to this shelf.'}</p></div><span className="text-xs text-slate-600 bg-slate-100 rounded-full px-3 py-1.5">{scan.mode === 'replay' ? (retail ? 'Saved manual sample' : 'Saved sample') : 'Photo analysis'}</span></div>
    <dl className="grid sm:grid-cols-3 gap-3">{rows.map(row => <div key={row.label} className={`rounded-xl border p-4 ${row.tone}`}><dt className="text-sm font-semibold">{row.label}</dt><dd className="text-3xl font-bold tabular-nums mt-1">{row.value}</dd><p className="text-sm leading-5 mt-2">{row.description}</p></div>)}</dl>
    <p className="text-xs text-slate-600 leading-5 mt-4">{counts.matched} matched + {counts.possible} possible + {counts.unidentified} not identified = {counts.expected} {retail ? 'products on the shelf list. These are product identities by name, variant, and package format, not unit counts or verified exact SKUs.' : 'titles on the shelf list. These are book names, not physical copy counts.'}</p>
    <p className="text-xs text-slate-600 leading-5 mt-1">{scan.reading_mode === 'single_pass' ? 'Read once; matches have not been independently verified. ' : ''}{retail ? 'Not identified does not mean out of stock. Saved readings are partial; inspect the photo and shelf before taking action.' : 'Not identified does not mean a book is missing. Check the photo before taking action.'}</p>
  </section>;
}
