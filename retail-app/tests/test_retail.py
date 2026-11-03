import asyncio
import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

from retail.compare import compare, fuse, same_size
from retail.models import ProductMaster, ProductObservation, ShelfAllocation, Extraction
from retail import main


def product(sku='a',size='12 oz',variant='Original',pack=1):
    return ProductMaster(sku_id=sku,brand='Demo',name='Oat Rings',variant=variant,size=size,pack_count=pack)


def observation(**kw):
    return ProductObservation(**dict(instance_id='p1',brand_text='Demo',product_name_text='Oat Rings',variant_text='Original',size_text='12 oz',pack_count_text='1',visible_text='Demo Oat Rings Original 12 oz',box_2d=[10,10,100,100])|kw)


def audit(obs,cat):
    return compare(obs,cat,[ShelfAllocation(allocation_id=p.sku_id,bay_id='cereal',sku_id=p.sku_id) for p in cat],'cereal')


def test_size_ambiguity_does_not_arbitrarily_assign_sku():
    r=audit([observation(size_text=None)],[product(),product('b','20 oz')])
    assert r.counts==dict(found=0,review=2,not_observed=0,expected=2)
    assert r.unresolved[0]['candidate_sku_ids']==['a','b']
    assert r.unresolved[0]['matched_sku_id'] is None


@pytest.mark.parametrize('change',[{'size_text':'20 oz'},{'variant_text':'Chocolate'},{'pack_count_text':'6'},{'size_text':'12 fl oz'},{'barcode_text':'123'}])
def test_visible_conflicts_reject(change):
    r=audit([observation(**change)],[product()])
    assert r.counts['found']==0 and r.counts['not_observed']==1


def test_units_preserve_dimension():
    assert same_size('1 kg','1000 g')
    assert same_size('12 oz','340.194 g')
    assert not same_size('12 oz','12 fl oz')


def test_cross_crop_fusion_keeps_adjacent_packages_and_partial_edges():
    a=observation(crop_id='a')
    b=observation(instance_id='p2',crop_id='b')
    c=observation(instance_id='p3',crop_id='b',box_2d=[10,110,100,200])
    partial=observation(instance_id='p4',crop_id='c',is_partial=True)
    assert len(fuse([a,b,c,partial]))==3
    r=audit([a,b,c],[product()])
    assert r.counts['found']==1 and r.visible_instances==2


def test_unknown_geometry_is_not_a_facing_count():
    r=audit([observation(box_2d=None),observation(instance_id='p2',box_2d=None)],[product()])
    assert len(r.observations)==2 and r.visible_instances is None


@pytest.mark.parametrize('box',[[0,0,0,10],[-1,2,3,4],[0,0,1001,30],[1,2,3]])
def test_invalid_boxes_rejected(box):
    with pytest.raises(ValidationError): observation(box_2d=box)


def test_nearby_price_label_does_not_fill_missing_size():
    extraction=Extraction(products=[observation(size_text=None)],labels=[dict(label_id='l1',visible_text='Oat Rings 12 oz $3',box_2d=[101,10,120,100])])
    r=main.result(extraction,'cereal','test')
    assert r['label_association']=='unavailable'
    assert r['observations'][0]['size_text'] is None


def test_sample_api_and_recompare_do_not_extract(monkeypatch):
    async def forbidden(*args): raise AssertionError('No inference allowed')
    monkeypatch.setattr(main,'extract',forbidden)
    with TestClient(main.app) as c:
        sample=c.get('/api/sample').json()
        assert sum(sample['counts'][s] for s in ('found','review','not_observed'))==sample['counts']['expected']
        r=c.post('/api/recompare',json={'bay_id':'pantry','extraction':sample['extraction']})
        assert r.status_code==200 and r.json()['counts']['not_observed']==2
        assert c.get('/api/sample?bay_id=bad').status_code==404


def test_upload_auth_and_failed_analysis_preserves_completion(tmp_path,monkeypatch):
    monkeypatch.setattr(main.uploads,'UPLOADS_DIR',tmp_path)
    image=io.BytesIO();Image.new('RGB',(20,20)).save(image,format='PNG')
    async def fail(*args): raise main.RecognitionError('Mock failure')
    monkeypatch.setattr(main,'extract',fail)
    with TestClient(main.app) as c:
        photo=c.post('/api/uploads?filename=test.png',content=image.getvalue()).json()
        previous={'sentinel':'completed-result'}
        main.uploads.save_analysis(photo['upload_id'],'bay_cereal',previous)
        payload={'upload_id':photo['upload_id'],'bay_id':'cereal'}
        assert c.post('/api/scan/stream',json=payload).status_code==401
        response=c.post('/api/scan/stream',json=payload,headers={'Authorization':'Bearer mock-session'})
        assert 'Mock failure' in response.text
        assert c.get(f"/api/uploads/{photo['upload_id']}/result").json()==previous
        assert c.post('/api/uploads',content=b'not a photo').status_code==422


def test_cancelled_stream_preserves_previous_result(tmp_path,monkeypatch):
    monkeypatch.setattr(main.uploads,'UPLOADS_DIR',tmp_path)
    image=io.BytesIO();Image.new('RGB',(20,20)).save(image,format='PNG')
    photo=main.uploads.save_upload(image.getvalue(),'test.png')
    previous={'sentinel':'previous-completion'}
    main.uploads.save_analysis(photo['upload_id'],'bay_cereal',previous)
    cancelled=[]
    async def blocked(raw,token,emit):
        try:
            await emit({'status':'reading','message':'Mock reading'})
            await asyncio.Event().wait()
        finally: cancelled.append(True)
    monkeypatch.setattr(main,'extract',blocked)
    class Request:
        async def is_disconnected(self): return False
    async def run():
        response=await main.scan(main.Scan(upload_id=photo['upload_id'],bay_id='cereal'),Request(),'Bearer mock')
        iterator=response.body_iterator
        assert 'Mock reading' in await anext(iterator)
        await iterator.aclose()
        assert not main.lock.locked()
    asyncio.run(run())
    assert cancelled==[True]
    assert main.saved(photo['upload_id'])==previous


def test_real_extraction_pipeline_with_mocked_company_sse():
    import httpx
    image=io.BytesIO();Image.new('RGB',(1800,800)).save(image,format='PNG')
    calls=[]
    extraction=Extraction(products=[observation()],labels=[]).model_dump()
    def handler(request):
        body=json.loads(request.content)
        assert request.headers['authorization']=='Bearer mock:llmproxy-playground'
        assert 'DEMO-001' not in json.dumps(body)
        assert 'products' in body['generationConfig']['responseJsonSchema']['properties']
        calls.append(request)
        event={'modelVersion':'gemini-3.1-pro-preview','candidates':[{'content':{'parts':[{'text':json.dumps(extraction)}]},'finishReason':'STOP'}]}
        return httpx.Response(200,text='data: '+json.dumps(event)+'\n\n',headers={'content-type':'text/event-stream'})
    async def run():
        events=[]
        async def emit(e): events.append(e)
        parsed,audit=await main.extract(image.getvalue(),'mock',emit,transport=httpx.MockTransport(handler))
        assert len(calls)==2 and len(parsed.products)==2
        assert parsed.products[0].box_2d != parsed.products[1].box_2d
        assert len(audit)==2 and len(events)==2
        assert 'mock' not in json.dumps(audit)
    asyncio.run(run())
