"""One origin for the selector, two retail photos, and original bookshelf API."""
import asyncio
import contextlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'bookshelf-original'
sys.path.insert(0, str(BASE))
from server.main import app as bookshelf_api
from server.recognition import RecognitionError
from retail.recognition import extract
from retail.identity import MATCHING_VERSION, match_identity
from retail.saved_runs import load_run, save_run
from retail.deduplication import deduplicate

PUBLIC = ROOT / 'app/public'
DIST = ROOT / 'app/dist'
app = FastAPI(title='Shelf Check · Retail & Bookshelf')
logger = logging.getLogger(__name__)
# Keep every original bookshelf endpoint and its authentication/inference path.
# Do not import the legacy retail.main module: it redirects global book uploads.
for route in bookshelf_api.routes:
    if getattr(route, 'path', '').startswith('/api/'):
        app.router.routes.append(route)


def store():
    return json.loads((PUBLIC / 'data/retail/store.json').read_text(encoding='utf-8'))


def get_sample(bay_id):
    if bay_id not in {b['id'] for b in store()['bays']}:
        raise HTTPException(404, 'Retail shelf not found')
    return json.loads((PUBLIC / f'data/retail/scans/{bay_id}.json').read_text(encoding='utf-8'))


def live_result(extraction, bay_id):
    """Match independent name/variant/format evidence against the whole catalogue."""
    result = get_sample(bay_id)
    catalogue = list(store()['catalogue'].values())
    assigned = {p['sku'] for p in result['planogram_items']}
    observations=[]; tasks=[]; matched=set(); possible=set(); linked_readings=0
    products, duplicates = deduplicate(extraction.products)
    for obs in products:
        identity=match_identity(obs,catalogue)
        candidates=identity.candidates
        linked_readings+=bool(candidates)
        resolved=identity.resolved
        if not candidates:
            candidates=[None]
        for item in candidates:
            sku=item['sku'] if item else None
            box=obs.box_2d
            row=dict(id=f'live-{obs.instance_id}-{sku or "unknown"}',title=item['title'] if item else (' · '.join(dict.fromkeys(v for v in (obs.product_name_text,obs.variant_text,obs.package_format_text) if v)) or obs.visible_text or 'Unidentified package'),
                author=obs.brand_text,sku=sku,confidence=None,
                box=dict(top=box[0]/1000,left=box[1]/1000,width=(box[3]-box[1])/1000,height=(box[2]-box[0])/1000) if box else None,
                box_source='model_estimate' if box else 'unavailable',verification_status='single_pass',visible_text=obs.visible_text,
                title_status='single_read' if resolved else 'uncertain',position_status='estimated' if box else 'needs_review',
                catalogue_status='matched' if item else 'unlisted',status='matched' if resolved and sku in assigned else 'needs_review',
                status_label='Matched product name & format' if resolved and sku in assigned else 'Product identity needs review',review_reasons=identity.reasons,recognition_evidence=obs.model_dump())
            observations.append(row)
            if sku in assigned:
                (matched if row['status']=='matched' else possible).add(sku)
        if not resolved:
            row=observations[-1]
            tasks.append(dict(id='identity-'+obs.instance_id,type='recognition_review',severity='medium',badge='Product identity',title=obs.visible_text or row['title'],
                author=obs.brand_text,shelf_item_id=row['id'],headline=' '.join(identity.reasons) or 'Confirm the product name, variant and selling format.',suggested_action='Mark identity check reviewed',requires_review=True))
        elif candidates[0]['sku'] not in assigned:
            item=candidates[0]
            tasks.append(dict(id='placement-'+obs.instance_id,type='misplaced_item',severity='medium',badge='Shelf assignment',title=item['title'],author=item['brand'],
                shelf_item_id=observations[-1]['id'],headline='The readable product belongs to another demo catalogue. Check the shelf assignment.',suggested_action='Mark placement check reviewed',requires_review=True))
    possible-=matched
    unseen=assigned-matched-possible
    for sku in sorted(unseen):
        item=next(p for p in result['planogram_items'] if p['sku']==sku)
        tasks.append(dict(id='unseen-'+sku,type='missing_item',severity='medium',badge='Not identified',title=item['title'],author=item['brand'],sku=sku,
            headline='Not identified in this model reading. It may be hidden, unreadable, or missed. Confirm in person before changing stock.',suggested_action='Mark shelf check reviewed',requires_review=True))
    result.update(mode='live',model='Company grocery vision',reading_mode='single_pass',scanned_at=datetime.now(timezone.utc).isoformat(),shelf_items=observations,action_tasks=tasks)
    result['metrics'].update(shelf_items_detected=len(products),matched_count=len(matched),review_count=len(possible),missing_count=len(unseen))
    result['missing_items']=[]
    result['misplaced_items']=[]
    result['metrics']['planogram_compliance_pct']=None
    result['matching_version']=MATCHING_VERSION
    result['recognition_diagnostics']={
        'package_readings':len(extraction.products),
        'retained_readings':len(products),
        'duplicate_readings':duplicates,
        'candidate_rows':len(observations),
        'named_readings':sum(bool(o.product_name_text) for o in extraction.products),
        'catalogue_linked_readings':linked_readings,
        'unlinked_readings':sum(o['sku'] is None for o in observations),
    }
    result['disclosure']='New company model reading. Exact sizes, GTINs, physical unit counts and stockouts are not established. Inventory is simulated. No saved manual readings were substituted.'
    return result


@app.get('/api/retail/results/{bay_id}')
def saved_retail_result(bay_id: str):
    sample=get_sample(bay_id)
    saved=load_run(bay_id, PUBLIC/'retail-photos'/sample['photo_filename'])
    if saved is None:
        return {'result':None}
    # Recompare saved raw readings with current matching rules, without another
    # company model request. Never use a saved result from the other photo.
    result=live_result(saved['extraction'],bay_id)
    result.update(run_id=saved['run_id'],scanned_at=saved['completed_at'])
    return {'result':result}


class RetailScan(BaseModel):
    model_config = ConfigDict(extra='forbid')
    bay_id: str = Field(pattern=r'^bay_(cereal|drinks)$')
    mode: Literal['live', 'replay'] = 'replay'


@app.post('/api/retail/scan/stream')
async def scan_retail(body: RetailScan, authorization: str | None = Header(default=None)):
    sample = get_sample(body.bay_id)
    if body.mode == 'replay':
        async def replay():
            yield 'data: ' + json.dumps({'step':4,'status':'complete','result':sample}) + '\n\n'
        return StreamingResponse(replay(), media_type='text/event-stream')
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Sign in to Straive to run a new retail analysis.')
    token=authorization[7:].strip()
    if not token or len(token)>4096 or '\r' in token or '\n' in token:
        raise HTTPException(401, 'Sign in again to run a retail analysis.')
    # Share the bookshelf scan lock so switching demos cannot multiply paid runs.
    from server.main import _live_scan_lock
    if _live_scan_lock.locked():
        raise HTTPException(409, 'Another shelf analysis is already running.')
    async def events():
        queue=asyncio.Queue()
        async def emit(event):
            await queue.put({'step':1, **event})
        async def work():
            if _live_scan_lock.locked():
                await queue.put({'status':'error','message':'Another shelf analysis is already running.'})
                return
            async with _live_scan_lock:
                try:
                    raw=(PUBLIC / 'retail-photos' / sample['photo_filename']).read_bytes()
                    extraction, audit = await extract(raw,token,emit)
                    result=live_result(extraction,body.bay_id)
                    result['run_id']=save_run(body.bay_id,raw,extraction,audit,result['scanned_at'])
                    await queue.put({'step':4,'status':'complete','result':result})
                except RecognitionError as exc:
                    await queue.put({'status':'error','message':str(exc)})
                except Exception:
                    logger.exception('Unexpected retail analysis failure')
                    await queue.put({'status':'error','message':'Live retail analysis did not complete. The previous result is unchanged.'})
        task=asyncio.create_task(work())
        try:
            while True:
                try: event=await asyncio.wait_for(queue.get(), timeout=10)
                except asyncio.TimeoutError:
                    yield ': keepalive\n\n'
                    continue
                yield 'data: '+json.dumps(event)+'\n\n'
                if event['status'] in {'error','complete'}: break
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError): await task
    return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})


# Serve only the two selected retail assets, not the six-photo source archive.
FRONTEND = DIST if DIST.is_dir() else PUBLIC
for folder in ('assets','data','photos','retail-photos'):
    if (FRONTEND / folder).is_dir():
        app.mount('/'+folder,StaticFiles(directory=FRONTEND/folder),name=folder)


@app.get('/{path:path}')
def frontend(path: str):
    if path.startswith('api/'):
        raise HTTPException(404,'API endpoint not found')
    file=(FRONTEND/path).resolve()
    if FRONTEND.resolve() in file.parents and file.is_file():
        return FileResponse(file)
    if path not in {'','retail','retail/analysis','bookshelf','bookshelf/analysis','bookshelf/model-comparison','analysis','model-comparison'}:
        raise HTTPException(404,'Page not found')
    return FileResponse(FRONTEND/'index.html')
