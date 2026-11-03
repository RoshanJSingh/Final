"""Offline by default. Optional bounded Foundry judge experiment is explicit."""
import argparse
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import demo
from retail.identity import match_identity
from retail.judge import adjudicate, retrieve_candidates
from retail.models import ProductObservation, Extraction
from retail.saved_runs import load_run


def baseline():
    spec=importlib.util.spec_from_file_location('retail.evaluation_baseline',ROOT/'qa/evaluation/identity_v3.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module.match_identity


async def evaluate(args):
    catalogue=list(demo.store()['catalogue'].values())
    cases=json.loads((ROOT/'qa/evaluation/cases.json').read_text(encoding='utf-8'))
    methods={'A_baseline':baseline(),'B_improved':match_identity}
    report={'scope':'Two-photo development evaluation; not general accuracy or fresh extraction quality.',
            'judge_enabled_in_app':False,'judge_experiment':'not run','methods':{},'saved_readings':{}}
    for name,matcher in methods.items():
        rows=[]; start=time.perf_counter()
        for case in cases:
            obs=ProductObservation.model_validate(case['observation']); result=matcher(obs,catalogue)
            selected=result.candidates[0]['sku'] if result.resolved else None
            expected=case['expected_auto']
            rows.append({'id':case['id'],'source':case['source'],'split':case['split'],
                'expected_auto':expected,'selected':selected,'possible':bool(result.candidates) and not result.resolved,
                'correct_auto':selected is not None and selected==expected,
                'incorrect_auto':selected is not None and selected!=expected,
                'missed_supported':expected is not None and selected!=expected,
                'appropriate_abstention':expected is None and selected is None,
                'candidate_retrieved':case['candidate_target'] in [p['sku'] for p in retrieve_candidates(obs,catalogue)] if case['candidate_target'] else None})
        metric=lambda field,den: {'numerator':sum(bool(r[field]) for r in rows),'denominator':den}
        report['methods'][name]={'cases':len(rows),'correct_auto':metric('correct_auto',sum(r['expected_auto'] is not None for r in rows)),
            'incorrect_auto':metric('incorrect_auto',sum(r['selected'] is not None for r in rows)),
            'possible':metric('possible',len(rows)),'missed_supported':metric('missed_supported',sum(r['expected_auto'] is not None for r in rows)),
            'appropriate_abstention':metric('appropriate_abstention',sum(r['expected_auto'] is None for r in rows)),
            'retrieval_coverage':metric('candidate_retrieved',sum(r['candidate_retrieved'] is not None for r in rows)),
            'latency_seconds':time.perf_counter()-start,'model_calls':0,'rows':rows}
    for bay in ['bay_cereal','bay_drinks']:
        sample=demo.get_sample(bay); saved=load_run(bay,demo.PUBLIC/'retail-photos'/sample['photo_filename'])
        if saved is None: report['saved_readings'][bay]={'available':False};continue
        products=saved['extraction'].products
        entry={'run_id':saved['run_id'],'image_sha256':saved['image_sha256'],'observation_count':len(products),
               'missing_product_name':sum(not o.product_name_text for o in products),
               'historical_model_calls':len(saved['sections']),
               'historical_total_tokens':sum((s.get('usage') or {}).get('totalTokenCount',0) for s in saved['sections']),
               'cost_usd':None,'accuracy':'Not fully labelled: counts below are acceptance counts, not correct-match metrics.'}
        for name,matcher in methods.items():
            matches=[m.candidates[0]['sku'] for o in products if (m:=matcher(o,catalogue)).resolved]
            entry[name]={'automatic_observations':{'numerator':len(matches),'denominator':len(products)},
                         'unique_catalogue_identities':{'numerator':len(set(matches)),'denominator':len(sample['planogram_items'])}}
        report['saved_readings'][bay]=entry
    if args.judge != 'off':
        token=os.environ.get('RETAIL_JUDGE_TOKEN')
        if not token: raise SystemExit('Set RETAIL_JUDGE_TOKEN to your existing company session token; never put it on the command line.')
        eligible=[c for c in cases if args.judge=='all' or not match_identity(ProductObservation.model_validate(c['observation']),catalogue).resolved]
        outcomes=[];start=time.perf_counter()
        for case in eligible[:args.max_observations]:
            result=await adjudicate(ProductObservation.model_validate(case['observation']),catalogue,token,cache_dir=ROOT/'output/judge-cache')
            outcomes.append({'id':case['id'],**result})
        report['judge_experiment']={'mode':args.judge,'max_calls':2*args.max_observations,'latency_seconds':time.perf_counter()-start,
            'calls':sum(r['calls'] for r in outcomes),'rows':outcomes,'cost_usd':None,
            'note':'New recommendations remain possible matches. Review against independent labels before considering deployment.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(args.output)
    for name,value in report['methods'].items(): print(name,{k:v for k,v in value.items() if k!='rows'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'qa/evaluation/results.json')
    parser.add_argument('--judge',choices=['off','hybrid','all'],default='off')
    parser.add_argument('--max-observations',type=int,choices=range(1,21),default=10)
    asyncio.run(evaluate(parser.parse_args()))
