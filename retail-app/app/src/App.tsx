import { useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, BookOpen, Layers, ShoppingBasket } from 'lucide-react';
import { BookshelfApp } from './BookshelfApp';
import { AnalysisPage } from './components/AnalysisPage';
import { DemoContext } from './demoContext';
import { checkFoundrySession, foundryLoginUrl, type FoundryAuthState } from './foundryAuth';
import type { StoreData } from './types';

function Brand() {
  return <a href="/" className="flex items-center gap-2.5 text-lg font-bold tracking-tight"><span className="w-9 h-9 rounded-xl bg-blue-600 text-white grid place-items-center"><Layers className="w-5 h-5" /></span>Shelf Check</a>;
}

function DemoHome() {
  return <div className="min-h-dvh bg-[#f7f9fc] text-slate-900 flex flex-col">
    <header className="bg-white border-b border-slate-200/80"><div className="max-w-6xl mx-auto px-5 sm:px-8 h-20 flex items-center justify-between"><Brand /><span className="text-xs text-slate-500">Straive · Shelf intelligence</span></div></header>
    <main className="w-full max-w-5xl mx-auto px-5 sm:px-8 py-14 sm:py-24 flex-1">
      <span className="inline-flex rounded-full bg-blue-50 border border-blue-100 px-3 py-1.5 text-[11px] font-semibold tracking-wide text-blue-700">PHOTO TO PLANOGRAM</span>
      <h1 className="mt-6 text-4xl sm:text-5xl font-semibold tracking-[-0.045em]">One clear view of your shelf.</h1>
      <p className="mt-5 text-base leading-7 text-slate-500">Choose a demo to explore the photo, compare the catalogue, and review what needs a closer look.</p>
      <div className="grid sm:grid-cols-2 gap-5 mt-10">
        {[
          { name: 'Retail', href: '/retail', Icon: ShoppingBasket, caption: 'Cereals, soft drinks & multipacks', description: 'Two grocery shelf photos. Product variants, package formats, and inventory checks in one familiar view.', count: '2 shelf photos' },
          { name: 'Bookshelf', href: '/bookshelf', Icon: BookOpen, caption: 'The original bookshelf demo', description: 'Open the existing bookshelf experience, with its photo upload, catalogue comparison, and shelf results.', count: 'Original experience' },
        ].map(({ name, href, Icon, caption, description, count }) => <article key={name} className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-[0_12px_40px_-24px_rgba(15,23,42,0.3)] flex flex-col">
          <span className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 grid place-items-center"><Icon className="w-6 h-6" /></span>
          <h2 className="text-2xl font-semibold tracking-tight mt-6">{name}</h2><p className="text-xs font-medium text-blue-700 mt-2">{caption}</p>
          <p className="text-sm text-slate-500 leading-6 mt-4 flex-1">{description}</p><p className="text-xs text-slate-400 mt-6 mb-4">{count}</p>
          <a role="button" href={href} className="inline-flex items-center justify-between rounded-xl bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 text-sm font-semibold">{name}<ArrowRight className="w-4 h-4" /></a>
        </article>)}
      </div>
    </main><footer className="text-center text-xs text-slate-400 px-5 py-6">Shelf Check · Simulated planogram and inventory records</footer>
  </div>;
}

function RetailApp() {
  const [location, setLocation] = useState(() => window.location.pathname + window.location.search);
  const [store, setStore] = useState<StoreData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [auth, setAuth] = useState<FoundryAuthState>({ status: 'checking' });
  const refreshAuth = () => { void checkFoundrySession().then(setAuth); };
  const signIn = () => window.location.assign(foundryLoginUrl(window.location.href));
  useEffect(() => {
    const controller = new AbortController();
    fetch('/data/retail/store.json', { signal: controller.signal }).then(r => { if (!r.ok) throw new Error('Retail records could not be loaded. Please reload to retry.'); return r.json(); }).then(setStore).catch(e => { if (e.name !== 'AbortError') setError(e.message); });
    refreshAuth();
    const pop = () => setLocation(window.location.pathname + window.location.search);
    window.addEventListener('popstate', pop);
    return () => { controller.abort(); window.removeEventListener('popstate', pop); };
  }, []);
  const navigate = (path: string) => { window.history.pushState(null, '', path); setLocation(path); window.scrollTo(0, 0); };
  const url = new URL(location, window.location.origin);
  const bayId = url.searchParams.get('bay') || 'bay_cereal';
  if (url.pathname === '/retail/analysis') return <AnalysisPage key={bayId} bayId={bayId} uploadId={null} store={store}
    health={{ live_available_by_difficulty: { retail: true } }} healthChecked auth={auth} onSignIn={signIn} onRefreshAuth={refreshAuth}
    onAuthenticationFailure={() => setAuth({ status: 'signed-out', message: 'Sign in again to run a new analysis.' })}
    storeError={error} onHome={() => navigate('/retail')} onSelectBay={id => navigate(`/retail/analysis?bay=${encodeURIComponent(id)}`)} />;
  return <div className="min-h-dvh bg-[#f7f9fc] text-slate-900 flex flex-col">
    <header className="bg-white border-b border-slate-200/80"><div className="max-w-6xl mx-auto px-5 sm:px-8 h-20 flex items-center justify-between"><Brand /><a href="/" className="inline-flex gap-1.5 text-sm text-slate-600 hover:text-blue-700"><ArrowLeft className="w-4 h-4" /> All demos</a></div></header>
    <main className="w-full max-w-6xl mx-auto px-5 sm:px-8 py-12 sm:py-16 flex-1">
      <span className="inline-flex rounded-full bg-blue-50 border border-blue-100 px-3 py-1.5 text-[11px] font-semibold tracking-wide text-blue-700">RETAIL SHELF CHECK</span>
      <h1 className="mt-6 text-4xl sm:text-5xl font-semibold tracking-[-0.045em]">A clear picture of your <span className="text-blue-600">shelf.</span></h1>
      <p className="mt-5 text-base leading-7 text-slate-500 max-w-2xl">Choose one of the two photos. Compare visible products with the demo inventory, then review possible discrepancies.</p>
      {error && <p role="alert" className="mt-8 text-red-700">{error}</p>}
      {!store && !error && <p role="status" className="mt-8 text-slate-500">Loading the two retail shelves…</p>}
      <div className="grid md:grid-cols-2 gap-6 mt-9">{store?.bays.map(bay => <article key={bay.id} className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-[0_12px_40px_-24px_rgba(15,23,42,0.3)]">
        <button onClick={() => navigate(`/retail/analysis?bay=${bay.id}`)} aria-label={`Open ${bay.name}`} className="block w-full bg-slate-100"><img src={`/retail-photos/${bay.photo}`} alt={bay.name} className="w-full aspect-[4/3] object-contain" /></button>
        <div className="p-5 sm:p-6"><div className="text-[11px] text-blue-700 font-semibold tracking-wide">{bay.code} · {bay.expected_items_count} catalogue products</div><h2 className="text-xl font-semibold tracking-tight mt-2">{bay.name}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">{bay.description || bay.section}</p><button onClick={() => navigate(`/retail/analysis?bay=${bay.id}`)} className="mt-5 w-full flex items-center justify-between rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700">Open shelf check<ArrowRight className="w-4 h-4" /></button></div>
      </article>)}</div>
      <p className="mt-7 text-xs leading-5 text-slate-500">Saved samples use manually transcribed readings. Inventory quantities and shelf assignments are simulated. Products are grouped by visible name, variant, and package format; exact GTINs and hidden stock are not inferred.</p>
    </main>
  </div>;
}

export function App() {
  const path = window.location.pathname;
  if (path === '/retail' || path.startsWith('/retail/')) return <DemoContext.Provider value="retail"><RetailApp /></DemoContext.Provider>;
  if (path === '/bookshelf' || path.startsWith('/bookshelf/') || path === '/analysis' || path === '/model-comparison') return <BookshelfApp />;
  return <DemoHome />;
}
