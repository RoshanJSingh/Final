"""Save completed retail readings locally for zero-inference recomparison.

Only model evidence from the two configured photos is stored. Session tokens,
request headers and image payloads are never persisted. Failed/cancelled scans
cannot replace the last completed reading.
"""
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from .models import Extraction

RUNS_DIR=Path(__file__).resolve().parents[1]/'output/retail-runs'


def save_run(bay_id,raw,extraction,audit,completed_at):
    if bay_id not in {'bay_cereal','bay_drinks'}: raise ValueError('Invalid retail bay')
    run_id=uuid4().hex
    payload={
        'schema_version':1,'run_id':run_id,'bay_id':bay_id,
        'image_sha256':hashlib.sha256(raw).hexdigest(),'completed_at':completed_at,
        'extraction':extraction.model_dump(),
        'sections':[{'tile':s.get('tile'),'bounds':s.get('bounds'),'finish_reason':s.get('finish_reason'),'usage':s.get('usage')} for s in audit],
    }
    RUNS_DIR.mkdir(parents=True,exist_ok=True)
    path=RUNS_DIR/f'{bay_id}.json'
    temporary=RUNS_DIR/f'.{run_id}.tmp'
    try:
        temporary.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return run_id


def load_run(bay_id,photo_path):
    if bay_id not in {'bay_cereal','bay_drinks'}: raise ValueError('Invalid retail bay')
    path=RUNS_DIR/f'{bay_id}.json'
    if not path.is_file(): return None
    try:
        payload=json.loads(path.read_text(encoding='utf-8'))
        if payload.get('schema_version')!=1 or payload.get('bay_id')!=bay_id: return None
        if payload.get('image_sha256')!=hashlib.sha256(photo_path.read_bytes()).hexdigest(): return None
        payload['extraction']=Extraction.model_validate(payload['extraction'])
        if not isinstance(payload['run_id'],str) or not isinstance(payload['completed_at'],str): return None
        return payload
    except (ValueError,OSError,KeyError,TypeError):
        return None
