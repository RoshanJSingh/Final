import { useRetail } from '../demoContext';
import React, { useState } from 'react';
import type { ActionTask } from '../types';
import { Check, CheckCircle2, ClipboardCheck, Eye } from 'lucide-react';

interface Props {
  tasks: ActionTask[];
  onResolveTask: (taskId: string) => void;
  hoveredItemId?: string | null;
  onHoverItem?: (id: string | null) => void;
}
export const Step3DiscrepancyView: React.FC<Props> = ({ tasks, onResolveTask, hoveredItemId, onHoverItem }) => {
  const retail = useRetail();
  const [tab, setTab] = useState<'all' | 'placement' | 'reading' | 'unseen' | 'records' | 'reviewed'>('all');
  const displayed = tasks.filter(task => tab === 'reviewed' ? task.resolved : !task.resolved && (
    tab === 'all' || tab === 'placement' && task.type === 'misplaced_item' ||
    tab === 'reading' && task.type === 'recognition_review' || tab === 'unseen' && task.type === 'missing_item' || tab === 'records' && task.type === 'record_error'));
  const tabs = [
    ['all', 'All'], ['reading', 'Names to check'], ['placement', 'Other shelves'],
    ['unseen', 'Not identified'], ['records', 'Stock records'], ['reviewed', 'Reviewed'],
  ] as const;
  return <section className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex flex-col h-full">
    <div className="p-4 border-b border-slate-100 bg-slate-50/70">
      <h2 className="text-sm font-bold text-slate-900">What to check next</h2>
      <p className="text-xs text-slate-600 leading-5 mt-2">Suggestions for your review. {retail ? 'A product' : 'A title'} can have more than one check. Marking a check reviewed does not change the results above.</p>
    </div>
    <div className="p-3 border-b border-slate-100 flex flex-wrap gap-1.5" role="group" aria-label="Filter review checks">{tabs.map(([id, label]) => <button key={id} onClick={() => setTab(id)} aria-pressed={tab === id} className={`px-2.5 py-1.5 rounded-md text-[11px] font-medium ${tab === id ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>{label}</button>)}</div>
    <div className="flex-1 overflow-y-auto p-3 space-y-2.5 max-h-[580px]">
      {!displayed.length ? <div className="py-10 px-5 text-center"><CheckCircle2 className="w-8 h-8 mx-auto text-emerald-600 mb-3" /><p className="text-sm font-semibold text-slate-800">{tab === 'reviewed' ? 'No reviewed checks yet' : 'No open checks in this view'}</p><p className="text-xs text-slate-500 leading-5 mt-2">{tab === 'reviewed' ? 'Checks you acknowledge appear here.' : 'Check the recognized titles and the original photo before making inventory decisions.'}</p></div>
        : displayed.map(task => {
          const location = task.type === 'recognition_review' && task.badge.includes('Location');
          const amber = task.type === 'misplaced_item' || task.type === 'record_error';
          return <article key={task.id} onMouseEnter={() => onHoverItem?.(task.shelf_item_id ?? null)} onMouseLeave={() => onHoverItem?.(null)} className={`rounded-lg border p-3 transition-colors ${task.resolved ? 'border-emerald-200 bg-emerald-50/40' : amber ? 'border-amber-200 bg-amber-50/20' : 'border-slate-200 bg-white'} ${hoveredItemId === task.shelf_item_id ? 'ring-2 ring-blue-200' : ''}`}>
            <div className="flex items-center gap-2 mb-2"><span className={`text-[10px] font-semibold px-2 py-1 rounded-md ${task.resolved ? 'bg-emerald-100 text-emerald-800' : location ? 'bg-blue-50 text-blue-800' : amber ? 'bg-amber-100 text-amber-900' : 'bg-slate-100 text-slate-600'}`}>{task.resolved ? 'Reviewed' : task.badge}</span></div>
            <h3 className="text-xs font-semibold text-slate-900 leading-5">{task.title}</h3><p className="text-[11px] text-slate-500">{task.author || (retail ? 'Brand not confirmed' : 'Author not confirmed')}</p>
            <p className="text-[11px] text-slate-600 leading-5 my-2.5">{task.headline}</p>
            {task.resolved ? <div className="text-[11px] text-emerald-700 inline-flex items-center gap-1.5"><Check className="w-3.5 h-3.5" /> Reviewed in this demo session</div>
              : <button onClick={() => onResolveTask(task.id)} className="inline-flex items-center justify-center gap-1.5 w-full rounded-md border border-slate-200 bg-white py-2 px-2.5 text-[11px] font-semibold text-slate-700 hover:border-blue-300 hover:text-blue-700"><Eye className="w-3.5 h-3.5 shrink-0" />{task.suggested_action}</button>}
          </article>;
        })}
    </div>
    <div className="p-3 border-t border-slate-200 bg-slate-50 flex gap-2 items-start text-[10px] text-slate-500 leading-4"><ClipboardCheck className="w-3.5 h-3.5 shrink-0 mt-0.5" />Review only · Acknowledging a check does not change inventory, confirm an uncertain reading or increase coverage.</div>
  </section>;
};
