"""Offline regressions; mocked judge responses are not model evaluation."""
import asyncio
import json
from pathlib import Path
import pytest
import httpx
import demo
from retail.models import ProductObservation as Observation
from retail.identity import match_identity
from retail.recognition import crop_bounds
from retail.deduplication import deduplicate
from retail.judge import adjudicate, validate_decision, retrieve_candidates, cache_key

CAT=list(demo.store()['catalogue'].values())


def test_evaluation_labels_and_no_unsupported_promotion():
    cases=json.loads((Path(__file__).parents[1]/'qa/evaluation/cases.json').read_text(encoding='utf-8'))
    for case in cases:
        result=match_identity(Observation.model_validate(case['observation']),CAT)
        assert (result.candidates[0]['sku'] if result.resolved else None)==case['expected_auto'],case['id']


def test_manufacturer_alone_and_ambiguous_variant_do_not_resolve():
    for brand in ['Great Value','General Mills','Kelloggs','Coca-Cola','Monster Energy']:
        assert not match_identity(Observation(instance_id='x',brand_text=brand,package_format_text='plastic bottle'),CAT).resolved


def test_grid_covers_edges_without_near_duplicate_rows():
    boxes=crop_bounds(4032,3024)
    assert len(boxes)==9
    assert sorted({b[1] for b in boxes})==[0,712,1424]
    assert max(b[2] for b in boxes)==4032 and max(b[3] for b in boxes)==3024
    assert all(b[2]-b[0]<=1600 and b[3]-b[1]<=1600 for b in boxes)


def test_dedup_requires_geometry_cross_crop_and_equal_identity():
    a=Observation(instance_id='a',crop_id='1',product_name_text='Coke Cherry',box_2d=[0,0,100,100])
    same=a.model_copy(update={'instance_id':'b','crop_id':'2'})
    adjacent=a.model_copy(update={'instance_id':'c','crop_id':'2','box_2d':[0,100,100,200]})
    conflict=same.model_copy(update={'instance_id':'d','product_name_text':'Coke Vanilla'})
    kept,duplicates=deduplicate([a,same,adjacent,conflict])
    assert [p.instance_id for p in kept]==['a','c','d']
    assert duplicates[0]['observation_id']=='b'


def decision(obs,sku='R-02-002'):
    return {'observation_id':obs.instance_id,'candidate_id':sku,'decision':'match','evidence':['Cherry on plastic bottle'],
            'conflicting_attributes':[],'missing_distinguishing_attributes':[]}


def test_judge_invalid_and_uncertain_responses():
    obs=Observation(instance_id='a',product_name_text='Coke',package_format_text='plastic bottle')
    candidates=retrieve_candidates(obs,CAT)
    for change in [{'candidate_id':'invented'},{'observation_id':'other'},{'evidence':[]},{'conflicting_attributes':['Vanilla']}]:
        with pytest.raises(ValueError): validate_decision(json.dumps({**decision(obs),**change}),obs,candidates,CAT)
    assert validate_decision(json.dumps(decision(obs)),obs,candidates,CAT).decision=='possible'
    assert cache_key(obs,CAT,'model-a')!=cache_key(obs,CAT,'model-b')
    assert cache_key(obs,CAT,'model-a')!=cache_key(obs,CAT[:-1],'model-a')


def test_judge_success_cache_timeout_and_fallback(tmp_path):
    obs=Observation(instance_id='a',product_name_text='Coke Cherry',package_format_text='plastic bottle')
    calls=[]
    def success(request):
        calls.append(request)
        body=json.loads(request.content)
        assert 'untrusted data' in body['contents'][0]['parts'][0]['text']
        event={'candidates':[{'content':{'parts':[{'text':json.dumps(decision(obs))}]},'finishReason':'STOP'}]}
        return httpx.Response(200,text='data: '+json.dumps(event)+'\n\n')
    async def run():
        result=await adjudicate(obs,CAT,'test-only',transport=httpx.MockTransport(success),cache_dir=tmp_path)
        assert result['source']=='judge' and result['decision']['decision']=='match'
        cached=await adjudicate(obs,CAT,'test-only',transport=httpx.MockTransport(success),cache_dir=tmp_path)
        assert cached['source']=='cache' and len(calls)==1
        async def timeout(request): await asyncio.sleep(.1)
        result=await adjudicate(obs,CAT,'test-only',transport=httpx.MockTransport(timeout),timeout=.001)
        assert result['source']=='deterministic_fallback' and result['calls']==2
        def invalid(request): return httpx.Response(200,text='data: {}\n\n')
        result=await adjudicate(obs,CAT,'test-only',transport=httpx.MockTransport(invalid))
        assert result['source']=='deterministic_fallback' and result['calls']==2
    asyncio.run(run())
    assert all('test-only' not in p.read_text() for p in tmp_path.glob('*.json'))
