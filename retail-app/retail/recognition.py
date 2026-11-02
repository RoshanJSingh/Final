"""Grocery extraction reused from the prototype; no catalogue is sent to the model."""
import asyncio
import json
from pathlib import Path
from server.recognition import VisionClient, RecognitionError, load_image, encode_image
from .models import Extraction
PROMPT = (Path(__file__).resolve().parents[2] / 'planning/Albertsons_Retail_Prompts.md').read_text().split('```text\n')[1].split('```')[0]
PROMPT += "\nAlso include package_format_text for each product: carton, plastic bottle, glass bottle multipack, mini cans, can carton, can, or water case, only if its visible packaging supports it. Otherwise use null.\n"

PROMPT += """
Describe the visible retail selling unit, not the crop-wide stock total. If a
printed carton or cardboard carrier visibly groups bottles/cans, report that
multipack as one selling unit rather than counting both carrier and contents.
Loose bottles/cans remain individual units. Do not infer a multipack from
adjacent loose bottles, and do not invent a pack count.

Separate product_name_text and variant_text naturally; both are matched later.
Use package_format_text for visible packaging (PET/plastic bottle, glass bottle
multipack, mini-can multipack, can carton, single can, cereal carton, water case).
If material or carrier is not clear, say bottle/carton or use null. Do not guess.

Make uncertainty_reasons field-specific: size_unreadable, pack_count_unreadable,
barcode_unreadable, name_unreadable, variant_unreadable, package_format_unreadable,
or boundary_uncertain. If glare/occlusion affects only size or the boundary, use
that field-specific reason. Unreadable price/size/barcode does not make the
readable product name uncertain. These are not validated exact-SKU identities.
"""

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


