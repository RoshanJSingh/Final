"""Local grocery demo. Company integration reused without changing its baseline."""
import asyncio
import contextlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent/'bookshelf-original'
sys.path.insert(0,str(BASE))
from server import uploads
from server.recognition import VisionClient, RecognitionError, load_image, encode_image
from .models import Extraction, ProductMaster, ShelfAllocation, ProductObservation
from .compare import compare

uploads.UPLOADS_DIR=ROOT/'output/uploads'
app=FastAPI(title='Straive Grocery Shelf Audit',version='1.0')
lock=asyncio.Lock()
catalogue=json.loads((ROOT/'data/catalogue.json').read_text())
products=[ProductMaster(**p) for p in catalogue['products']]
allocations=[ShelfAllocation(**a) for a in catalogue['allocations']]
PROMPT=(ROOT.parent/'planning/Albertsons_Retail_Prompts.md').read_text().split('```text\n')[1].split('```')[0]


def result(extraction,bay,source):
    return {**compare(extraction.products,products,allocations,bay).model_dump(),'labels':[l.model_dump() for l in extraction.labels], 'extraction':extraction.model_dump(), 'source':source,'completed_at':datetime.now(timezone.utc).isoformat(),'provenance':('Generic CC0 retail photograph; partial manual readings.' if source=='manual_sample' else 'Uploaded or recomparison evidence; image rights and store context are not verified.')+' Simulated assortment. No retailer integration.','label_association':'unavailable','facing_note':'Unlocated or partial evidence prevents a reliable physical facing count.'}


@app.get('/api/health')
def health(): return {'status':'healthy','default_mode':'sample','schema_version':'1.0'}


@app.get('/api/catalogue')
def get_catalogue(): return {**catalogue,'bays':[{'id':'cereal','name':'Breakfast cereals','location':'Aisle 04 · Bay 02'},{'id':'pantry','name':'Pantry essentials','location':'Aisle 05 · Bay 01'}]}


@app.get('/api/sample')
def sample(bay_id: str='cereal'):
    validate_bay(bay_id)
    return result(Extraction(**json.loads((ROOT/'data/cereal-readings.json').read_text())),bay_id,'manual_sample')


def validate_bay(bay):
    if bay not in {'cereal','pantry'}: raise HTTPException(404,'Bay not found')


@app.get('/api/assets')
def assets(): return json.loads((ROOT.parent/'retail-images/manifest.json').read_text())


@app.post('/api/uploads',status_code=201)
async def upload(request:Request,filename:str='shelf-photo'):
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>20*1024*1024: raise HTTPException(413,'Choose an image smaller than 20 MB.')
    return await asyncio.to_thread(uploads.save_upload,bytes(raw),filename)


@app.get('/api/uploads/{upload_id}/image')
def image(upload_id:str):
    meta=uploads.get_upload(upload_id)
    return FileResponse(uploads.upload_directory(upload_id)/'image',media_type=meta['media_type'],headers={'Cache-Control':'private, no-store'})


@app.get('/api/uploads/{upload_id}/result')
def saved(upload_id:str,bay_id:str='cereal'):
    validate_bay(bay_id)
    path=uploads.saved_analysis_path(upload_id,"bay_"+bay_id)
    return json.loads(path.read_text()) if path.exists() else None


class Recompare(BaseModel):
    bay_id:str
    extraction:Extraction


@app.post('/api/recompare')
def recompare(body:Recompare):
    validate_bay(body.bay_id)
    return result(body.extraction,body.bay_id,'recomparison')


class Scan(BaseModel):
    upload_id:str
    bay_id:str


async def extract(raw,token,emit, *, transport=None):
    """Experimental 1600px/15% overlap grid; evaluated settings are not claimed."""
    image=load_image(raw)
    w,h=image.size
    edge=1600; stride=1360
    xs=list(range(0,max(w-edge,0)+1,stride)); ys=list(range(0,max(h-edge,0)+1,stride))
    if xs[-1]+edge<w: xs.append(w-edge)
    if ys[-1]+edge<h: ys.append(h-edge)
    bounds=[(x,y,min(x+edge,w),min(y+edge,h)) for y in ys for x in xs]
    if len(bounds)>32: raise RecognitionError('This photo needs too many crops. Please upload a closer bay photograph.')
    observations=[]; labels=[]; audit=[]
    async def read(box,tile,depth=0):
        await emit({'status':'reading','message':f'Reading section {tile} of {len(bounds)}. Keep this window open.'})
        crop=image.crop(box)
        body={'contents':[{'role':'user','parts':[{'inlineData':{'mimeType':'image/png','data':encode_image(crop)}},{'text':PROMPT}]}],'generationConfig':{'responseMimeType':'application/json','responseJsonSchema':Extraction.model_json_schema(),'maxOutputTokens':16384}}
        import httpx
        from server.recognition import FOUNDRY_ENDPOINT, FOUNDRY_PROJECT
        try:
            async with asyncio.timeout(240):
                async with httpx.AsyncClient(timeout=240,transport=transport) as http:
                    async with http.stream('POST',FOUNDRY_ENDPOINT,headers={'Authorization':f'Bearer {token}:{FOUNDRY_PROJECT}'},json=body) as response:
                        if response.status_code>=400: raise RecognitionError(f'Company inference returned HTTP {response.status_code}. Your previous result is safe.')
                        payload,finish,usage=await VisionClient._read_sse(response)
        except (httpx.HTTPError,TimeoutError) as exc:
            raise RecognitionError('Company inference could not complete. Check your connection and try again.') from exc
        finally: crop.close()
        text=''.join(p.get('text','') for p in payload['candidates'][0].get('content',{}).get('parts',[]) if not p.get('thought'))
        audit.append({'tile':str(tile),'bounds':box,'finish_reason':finish,'usage':usage,'response_text':text})
        if finish=='MAX_TOKENS' and depth<1:
            x0,y0,x1,y1=box; mid=(x0+x1)//2
            await read((x0,y0,mid,y1),f'{tile}.1',depth+1); await read((mid,y0,x1,y1),f'{tile}.2',depth+1)
            return
        if finish!='STOP': raise RecognitionError('Incomplete extraction was discarded. Your previous result is safe.')
        try: parsed=Extraction.model_validate_json(text)
        except ValueError as exc: raise RecognitionError('The extraction contained invalid evidence. No result was replaced.') from exc
        def mapped(box2):
            if box2 is None: return None
            y0,x0,y1,x1=box2; bx,by,ex,ey=box
            return [round((by+y0/1000*(ey-by))/h*1000),round((bx+x0/1000*(ex-bx))/w*1000),round((by+y1/1000*(ey-by))/h*1000),round((bx+x1/1000*(ex-bx))/w*1000)]
        for p in parsed.products:
            p.instance_id=f'{tile}-{p.instance_id}';p.crop_id=str(tile);p.box_2d=mapped(p.box_2d);observations.append(p)
        for label in parsed.labels:
            label.label_id=f'{tile}-{label.label_id}';label.box_2d=mapped(label.box_2d);labels.append(label)
    try:
        for i,box in enumerate(bounds): await read(box,i+1)
        return Extraction(products=observations,labels=labels),audit
    finally: image.close()


@app.post('/api/scan/stream')
async def scan(body:Scan,request:Request,authorization:str|None=Header(default=None)):
    validate_bay(body.bay_id)
    if not authorization or not authorization.startswith('Bearer ') or not authorization[7:].strip(): raise HTTPException(401,'Sign in with your Straive account to analyze a photo.')
    directory=uploads.upload_directory(body.upload_id)
    if lock.locked(): raise HTTPException(409,'Another analysis is running. Please wait.')
    await lock.acquire()
    async def stream():
        queue=asyncio.Queue()
        async def emit(value): await queue.put(value)
        async def work():
            try:
                extraction,audit=await extract((directory/'image').read_bytes(),authorization[7:],emit)
                if await request.is_disconnected(): return
                complete=result(extraction,body.bay_id,'live');complete['audit']=audit
                uploads.save_analysis(body.upload_id,"bay_"+body.bay_id,complete)
                await emit({'status':'complete','result':complete})
            except RecognitionError as exc: await emit({'status':'error','message':str(exc)})
            except Exception: await emit({'status':'error','message':'Analysis did not complete. Your previous result is safe.'})
            finally: await queue.put(None)
        task=asyncio.create_task(work())
        try:
            while True:
                event=await queue.get()
                if event is None: break
                yield 'data: '+json.dumps(event)+'\n\n'
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError): await task
            lock.release()
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-store'})


app.mount('/photos',StaticFiles(directory=ROOT.parent/'retail-images'),name='photos')
if (ROOT/'app/dist').exists():
    app.mount('/',StaticFiles(directory=ROOT/'app/dist',html=True),name='frontend')
