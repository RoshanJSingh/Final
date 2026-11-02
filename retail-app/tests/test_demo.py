"""Combined entry point and inventory integrity; all inference is mocked."""
import hashlib
import json
from fastapi.testclient import TestClient
import demo
from retail.models import Extraction, ProductObservation

client=TestClient(demo.app)


def test_only_two_retail_assets_are_served():
    records=json.loads((demo.ROOT/'data/retail-inventory.json').read_text())
    assert len(list((demo.PUBLIC/'retail-photos').glob('*.jpg')))==2
    for source in records['sources']:
        response=client.get('/retail-photos/'+source['filename'])
        assert response.status_code==200
        assert hashlib.sha256(response.content).hexdigest()==source['sha256']
    assert client.get('/retail-photos/03_canned_vegetable_variants.jpg').status_code==404
    assert client.get('/api/assets').status_code==404


def test_inventory_partition_and_unknown_attributes():
    store=demo.store()
    assert len(store['bays'])==2 and len(store['catalogue'])==44
    for bay in store['bays']:
        scan=demo.get_sample(bay['id'])
        expected={p['sku'] for p in scan['planogram_items']}
        matched={o['sku'] for o in scan['shelf_items'] if o['status']=='matched'}
        possible={o['sku'] for o in scan['shelf_items'] if o['status']!='matched'}-matched
        assert len(matched)+len(possible)+len(expected-matched-possible)==len(expected)
        assert scan['mode']=='replay' and scan['tokens_used'] is None
        assert all(p['price'] is None and p['physically_on_shelf'] is None and p['gtin'] is None for p in scan['planogram_items'])
        for o in scan['shelf_items']:
            b=o['box']
            assert 0<=b['left']<b['left']+b['width']<=1
            assert 0<=b['top']<b['top']+b['height']<=1
    coke=[p for p in store['catalogue'].values() if p['product_name']=='Coca-Cola Original Taste']
    assert len(coke)==3 and len({p['package_format'] for p in coke})==3


def test_entry_points_and_original_api():
    for page in ['/','/retail','/retail/analysis?bay=bay_drinks','/bookshelf','/bookshelf/analysis?bay=bay_f3','/bookshelf/model-comparison']:
        assert client.get(page).status_code==200
    assert len(client.get('/api/store').json()['bays'])>2
    assert client.get('/api/scan/bay_f3').status_code==200
    assert client.get('/api/health').json()['inference_authentication_required'] is True
    assert client.get('/api/unknown').status_code==404


def test_replay_has_no_auth_but_live_requires_it():
    assert client.post('/api/retail/scan/stream',json={'bay_id':'bay_drinks'}).status_code==200
    assert client.post('/api/retail/scan/stream',json={'bay_id':'bay_drinks','mode':'live'}).status_code==401
    assert client.post('/api/retail/scan/stream',json={'bay_id':'bay_pantry'}).status_code==422
    assert client.post('/api/retail/scan/stream',json={'bay_id':'bay_drinks','upload_id':'x'}).status_code==422


def test_live_does_not_guess_format_or_count_duplicates_as_unique_products():
    partial=ProductObservation(instance_id='a',product_name_text='Coca-Cola Original Taste',visible_text='Coca-Cola Original Taste')
    result=demo.live_result(Extraction(products=[partial],labels=[]),'bay_drinks')
    assert result['metrics']['matched_count']==0 and result['metrics']['review_count']==3
    full=partial.model_copy(update={'package_format_text':'plastic bottle'})
    result=demo.live_result(Extraction(products=[full,full.model_copy(update={'instance_id':'b'})],labels=[]),'bay_drinks')
    assert result['metrics']['matched_count']==1
    conflict=full.model_copy(update={'variant_text':'Cherry Vanilla'})
    assert demo.live_result(Extraction(products=[conflict],labels=[]),'bay_drinks')['metrics']['matched_count']==0


def test_mocked_live_uses_selected_photo_and_no_fallback(monkeypatch):
    seen=[]
    async def fake(raw,token,emit):
        seen.append(hashlib.sha256(raw).hexdigest())
        await emit({'status':'reading','message':'Mocked reading'})
        return Extraction(products=[],labels=[]),[]
    monkeypatch.setattr(demo,'extract',fake)
    r=client.post('/api/retail/scan/stream',json={'bay_id':'bay_drinks','mode':'live'},headers={'Authorization':'Bearer mock'})
    assert '"status": "complete"' in r.text and '"mode": "live"' in r.text
    assert seen==[hashlib.sha256((demo.PUBLIC/'retail-photos/02_soft_drinks_and_multipacks.jpg').read_bytes()).hexdigest()]
    async def fail(*args):
        raise demo.RecognitionError('Mocked inference failure')
    monkeypatch.setattr(demo,'extract',fail)
    r=client.post('/api/retail/scan/stream',json={'bay_id':'bay_cereal','mode':'live'},headers={'Authorization':'Bearer mock'})
    assert '"status": "error"' in r.text and '"result"' not in r.text
