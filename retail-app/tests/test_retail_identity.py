"""Regression examples are illustrative model-shaped readings, not a live run."""
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
import demo
from retail import saved_runs
from retail.identity import match_identity
from retail.models import Extraction, ProductObservation


def observation(name,brand=None,variant=None,fmt=None,count=None,size=None,uncertain=False,reasons=(),instance_id='p'):
    return ProductObservation(instance_id=instance_id,product_name_text=name,brand_text=brand,variant_text=variant,package_format_text=fmt,
        pack_count_text=count,size_text=size,uncertain=uncertain,uncertainty_reasons=list(reasons),visible_text=' '.join(v for v in (brand,name,variant) if v))


@pytest.fixture
def catalogue(): return list(demo.store()['catalogue'].values())


@pytest.mark.parametrize('obs,sku',[
 (observation('Coca-Cola','Coca-Cola','Original Taste','PET bottle',uncertain=True,reasons=['size_unreadable']),'R-02-001'),
 (observation('Coca Cola','Cocacola','Cherry','plastic bottles',uncertain=True,reasons=['barcode_unreadable']),'R-02-002'),
 (observation('Monster Energy','Monster','Original','aluminum can',uncertain=True,reasons=['size_unreadable']),'R-02-003'),
 (observation('Coca Cola','Coca-Cola','Zero Sugar','mini can multipack','10 pack','7.5 fl. oz.'),'R-02-005'),
 (observation('Sprite','Sprite','Lemon-Lime','cardboard box of mini cans','10 cans','222 ml'),'R-02-006'),
 (observation('Fanta','Fanta','Orange','can multipack','10','7.5 fl oz'),'R-02-007'),
 (observation('Coca-Cola','Coca-Cola','Georgia Peach','4-pack glass bottle carrier','4',uncertain=True,reasons=['size_unreadable']),'R-02-008'),
 (observation('Coca-Cola California Raspberry','Coca-Cola',fmt='glass bottles in cardboard carrier',count='4'),'R-02-009'),
 (observation('Coke Original','The Coca-Cola Company',fmt='6-pack glass bottles',count='6',uncertain=True,reasons=['barcode_unreadable']),'R-02-010'),
 (observation('Life','Coca-Cola',fmt='glass bottle multipack',count='4'),'R-02-011'),
 (observation('Sprite','Sprite','Lemon-Lime','glass bottle multipack','6'),'R-02-012'),
 (observation('Coca Cola','Coca-Cola','Classic','cardboard box of cans','24'),'R-02-013'),
 (observation('Coca-Cola Life','Coca-Cola',fmt='12-pack cans',count='12',uncertain=True,reasons=['size_unreadable']),'R-02-014'),
 (observation('Cherry Coke','Coca-Cola',fmt='can multipack',count='12'),'R-02-015'),
 (observation('Coca-Cola','Coca-Cola','Orange Vanilla','can carton'),'R-02-016'),
 (observation('Coke','Coca-Cola','Vanilla','can box'),'R-02-017'),
 (observation('Coca-Cola Zero','Coca-Cola','Zero Sugar','can carton',uncertain=True,reasons=['boundary_uncertain']),'R-02-018'),
 (observation('Purified Drinking Water','Aquafina',fmt='case',count='32',uncertain=True,reasons=['size_unreadable']),'R-02-019'),
 (observation('Coca-Cola Cherry','Coca-Cola','Cherry Cola','PET bottle'),'R-02-002'),
 (observation('Chex','Chex','Rice','cereal box',uncertain=True,reasons=['size_unreadable']),'R-01-011'),
 (observation('Cheerios','General Mills','Maple','carton'),'R-01-014'),
 (observation('Multigrain Cheerios','Cheerios',fmt='box'),'R-01-019'),
])
def test_equivalent_field_splits_and_non_identity_uncertainty(obs,sku,catalogue):
    match=match_identity(obs,catalogue)
    assert [p['sku'] for p in match.candidates]==[sku]
    assert match.resolved,match.reasons


@pytest.mark.parametrize('obs',[
 observation('Coca-Cola Cherry Vanilla','Coca-Cola',fmt='plastic bottle'),
 observation('Coca-Cola Original Taste','Coca-Cola','Cherry Vanilla','plastic bottle'),
 observation('Coca-Cola Cherry','Coca-Cola','Vanilla','plastic bottle'),
 observation('Sprite Cranberry','Sprite',fmt='glass bottle multipack',count='6'),
 observation('Monster Energy Ultra','Monster Energy',fmt='can'),
 observation('Rice Chex','Kelloggs',fmt='carton'),
 observation('Sprite Mini','Sprite',fmt='mini cans',count='6',size='7.5 fl oz'),
 observation('Sprite Mini','Sprite',fmt='mini cans',count='10',size='12 fl oz'),
 observation('Coca-Cola Original Taste','Coca-Cola',fmt='plastic bottle',count='6'),
])
def test_conflicts_and_unlisted_variants_are_not_promoted(obs,catalogue):
    assert not match_identity(obs,catalogue).resolved


@pytest.mark.parametrize('obs',[
 observation('Coca-Cola','Coca-Cola',fmt='plastic bottle'),
 observation('Coca-Cola Original Taste','Coca-Cola'),
 observation('Coca-Cola Cherry','Coca-Cola',fmt='bottle'),
 observation('Sprite Mini','Sprite',fmt='mini cans',count='10'),
 observation('Coca-Cola Original Taste','Coca-Cola',fmt='glass bottle'),
 observation('Coca-Cola Original Taste','Coca-Cola',fmt='plastic bottle',uncertain=True,reasons=['variant_unreadable']),
 observation('Coca-Cola Original Taste','Coca-Cola',fmt='plastic bottle',uncertain=True),
 observation('Coca-Cola Original Taste','Coca-Cola',fmt='plastic bottle',uncertain=True,reasons=['glare_on_name_and_size']),
 observation('Coca-Cola Original Taste','Coca-Cola',fmt='plastic bottle',uncertain=True,reasons=['barcode_and_variant_unreadable']),
])
def test_incomplete_identity_stays_for_review(obs,catalogue):
    match=match_identity(obs,catalogue)
    assert match.candidates
    assert not match.resolved


def test_saved_readings_recompare_without_new_inference(monkeypatch,tmp_path):
    monkeypatch.setattr(saved_runs,'RUNS_DIR',tmp_path/'runs')
    photo=demo.PUBLIC/'retail-photos/02_soft_drinks_and_multipacks.jpg'
    evidence=Extraction(products=[observation('Coca-Cola','Coca-Cola','Cherry','PET bottle')],labels=[])
    run_id=saved_runs.save_run('bay_drinks',photo.read_bytes(),evidence,[],'2026-11-02T10:00:00+00:00')
    def fail(*args): raise AssertionError('Loading must never call inference')
    monkeypatch.setattr(demo,'extract',fail)
    client=TestClient(demo.app)
    result=client.get('/api/retail/results/bay_drinks').json()['result']
    assert result['run_id']==run_id and result['metrics']['matched_count']==1
    assert result['shelf_items'][0]['sku']=='R-02-002'
    assert result['shelf_items'][0]['recognition_evidence']['variant_text']=='Cherry'
    assert client.get('/api/retail/results/bay_cereal').json()['result'] is None
    assert client.get('/api/retail/results/bay_pantry').status_code==404
    # Corrupt or mismatched saved evidence must not be attached to a photo.
    path=saved_runs.RUNS_DIR/'bay_drinks.json'
    payload=json.loads(path.read_text());payload['image_sha256']='incorrect'
    path.write_text(json.dumps(payload))
    assert client.get('/api/retail/results/bay_drinks').json()['result'] is None


def test_failed_live_run_keeps_previous_readings(monkeypatch,tmp_path):
    monkeypatch.setattr(saved_runs,'RUNS_DIR',tmp_path/'runs')
    raw=(demo.PUBLIC/'retail-photos/02_soft_drinks_and_multipacks.jpg').read_bytes()
    evidence=Extraction(products=[observation('Sprite',fmt='glass bottle multipack')],labels=[])
    run_id=saved_runs.save_run('bay_drinks',raw,evidence,[],'2026-11-02T10:00:00+00:00')
    async def fail(*args): raise demo.RecognitionError('Mocked failure')
    monkeypatch.setattr(demo,'extract',fail)
    response=TestClient(demo.app).post('/api/retail/scan/stream',json={'bay_id':'bay_drinks','mode':'live'},headers={'Authorization':'Bearer not-a-real-session'})
    assert '"status": "error"' in response.text
    assert saved_runs.load_run('bay_drinks',demo.PUBLIC/'retail-photos/02_soft_drinks_and_multipacks.jpg')['run_id']==run_id
    assert 'not-a-real-session' not in (saved_runs.RUNS_DIR/'bay_drinks.json').read_text()
