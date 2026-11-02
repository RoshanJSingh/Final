"""One origin for the selector, two retail photos, and original bookshelf API."""
import asyncio
import contextlib
import json
import re
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

PUBLIC = ROOT / 'app/public'
DIST = ROOT / 'app/dist'
app = FastAPI(title='Shelf Check · Retail & Bookshelf')
# Keep every original bookshelf endpoint and its authentication/inference path.
# Do not import the legacy retail.main module: it redirects global book uploads.
for route in bookshelf_api.routes:
    if getattr(route, 'path', '').startswith('/api/'):
        app.router.routes.append(route)


def store():
    return json.loads((PUBLIC / 'data/retail/store.json').read_text())


def get_sample(bay_id):
    if bay_id not in {b['id'] for b in store()['bays']}:
        raise HTTPException(404, 'Retail shelf not found')
    return json.loads((PUBLIC / f'data/retail/scans/{bay_id}.json').read_text())


def norm(value):
    return re.sub(r'\s+', ' ', re.sub(r'[^\w]+', ' ', (value or '').casefold())).strip()


def canonical_format(value):
    value = norm(value)
    for keys, label in [
        (('mini',), 'mini cans'),
        (('glass', 'multipack'), 'glass bottle multipack'),
        (('glass', 'pack'), 'glass bottle multipack'),
        (('plastic', 'bottle'), 'plastic bottle'),
        (('water', 'case'), 'water case'),
        (('can', 'carton'), 'can carton'),
        (('can', 'pack'), 'can carton'),
        (('carton',), 'carton'),
        (('can',), 'can'),
    ]:
        if all(k in value.split() for k in keys):
            return label
    return None


def expected_format(item):
    pack = item['package_format'].casefold()
    if '7.5' in pack: return 'mini cans'
    if 'glass' in pack: return 'glass bottle multipack'
    return canonical_format(pack)


def live_result(extraction, bay_id):
    """Match name/variant/format identities conservatively, never infer sizes.

    Exact normalized names only. An ambiguous format reserves every compatible
    catalogue candidate as possible. Matching is against the whole catalogue;
    selecting a bay never supplies missing identity evidence.
    """
    result = get_sample(bay_id)
    catalogue = list(store()['catalogue'].values())
    assigned = {p['sku'] for p in result['planogram_items']}
    observations=[]; tasks=[]; matched=set(); possible=set()
    for obs in extraction.products:
        name=norm(obs.product_name_text)
        variant=norm(obs.variant_text)
        forms={name, norm(f'{name} {variant}'), norm(f'{variant} {name}')}
        forms.discard('')
        product_format=canonical_format(obs.package_format_text)
        candidates=[]
        for item in catalogue:
            expected=norm(item['product_name'])
            if expected not in forms: continue
            # If the model supplies a more specific flavour, it must occur in
            # the catalogue name. Never turn an unfamiliar flavour into Original.
            if variant and variant not in {'original','original taste','lemon lime'} and variant not in expected:
                continue
            if obs.brand_text and norm(obs.brand_text) != norm(item['brand']):
                continue
            if product_format and product_format != expected_format(item):
                continue
            candidates.append(item)
        resolved=len(candidates)==1 and product_format is not None and not obs.uncertain
        if resolved and expected_format(candidates[0])=='mini cans':
            # These catalogue entries specify a ten-can pack. Do not promote
            # a generic mini-can observation to that exact selling format.
            resolved=norm(obs.pack_count_text) in {'10','10 cans'} and norm(obs.size_text) in {'7 5 fl oz','7 5 floz'}
        if not candidates:
            candidates=[None]
        for item in candidates:
            sku=item['sku'] if item else None
            box=obs.box_2d
            row=dict(id=f'live-{obs.instance_id}-{sku or "unknown"}',title=item['title'] if item else (obs.product_name_text or obs.visible_text or 'Unidentified package'),
                author=obs.brand_text,sku=sku,confidence=None,
                box=dict(top=box[0]/1000,left=box[1]/1000,width=(box[3]-box[1])/1000,height=(box[2]-box[0])/1000) if box else None,
                box_source='model_estimate' if box else 'unavailable',verification_status='single_pass',visible_text=obs.visible_text,
                title_status='single_read' if resolved else 'uncertain',position_status='estimated' if box else 'needs_review',
                catalogue_status='matched' if item else 'unlisted',status='matched' if resolved and sku in assigned else 'needs_review',
                status_label='Matched product name & format' if resolved and sku in assigned else 'Product identity needs review',review_reasons=obs.uncertainty_reasons)
            observations.append(row)
            if sku in assigned:
                (matched if row['status']=='matched' else possible).add(sku)
        if not resolved:
            row=observations[-1]
            tasks.append(dict(id='identity-'+obs.instance_id,type='recognition_review',severity='medium',badge='Product identity',title=obs.visible_text or row['title'],
                author=obs.brand_text,shelf_item_id=row['id'],headline='Confirm the product name, variant and selling format. No candidate is chosen by guessing.',suggested_action='Mark identity check reviewed',requires_review=True))
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
    result['metrics'].update(shelf_items_detected=len(observations),matched_count=len(matched),review_count=len(possible),missing_count=len(unseen))
    result['disclosure']='New company model reading. Exact sizes, GTINs, physical unit counts and stockouts are not established. Inventory is simulated. No saved manual readings were substituted.'
    return result


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
                    extraction, _ = await extract((PUBLIC / 'retail-photos' / sample['photo_filename']).read_bytes(),token,emit)
                    await queue.put({'step':4,'status':'complete','result':live_result(extraction,body.bay_id)})
                except RecognitionError as exc:
                    await queue.put({'status':'error','message':str(exc)})
                except Exception:
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
