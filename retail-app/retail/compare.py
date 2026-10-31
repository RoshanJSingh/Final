"""Deterministic, conflict-first matching. No retailer data or model scores."""
import re
import unicodedata
from .models import ComparisonResult, ProductObservation, ReviewTask


def norm(value):
    return re.sub(r'\s+', ' ', re.sub(r'[^\w]+', ' ', unicodedata.normalize('NFKC', value or '').lower())).strip()


def quantity(value):
    match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(kg|g|oz|lb|ml|l|fl\s*oz)\s*', value or '', re.I)
    if not match:
        return None
    amount, unit = float(match[1]), re.sub(r'\s+', '', match[2].lower())
    dimension, factor = {'kg': ('mass',1000),'g':('mass',1),'oz':('mass',28.349523125),'lb':('mass',453.59237),'ml':('volume',1),'l':('volume',1000),'floz':('volume',29.5735295625)}[unit]
    return dimension, amount*factor


def same_size(a, b):
    x, y = quantity(a), quantity(b)
    return x[0] == y[0] and abs(x[1]-y[1]) < max(x[1], y[1])*.005 if x and y else norm(a) == norm(b)


def valid_gtin(value):
    if not value or not value.isascii() or not value.isdigit() or len(value) not in (8,12,13,14):
        return False
    return (sum(int(c)*(3 if i%2 == 0 else 1) for i,c in enumerate(reversed(value[:-1]))) + int(value[-1])) % 10 == 0


def candidates(obs, catalogue):
    result=[]
    for p in catalogue:
        fields=[(obs.brand_text,p.brand),(obs.product_name_text,p.name),(obs.variant_text,p.variant)]
        if any(a and norm(a) != norm(b) for a,b in fields):
            continue
        if obs.size_text and not same_size(obs.size_text,p.size):
            continue
        if obs.pack_count_text and norm(obs.pack_count_text) != str(p.pack_count):
            continue
        if obs.barcode_text and (not valid_gtin(obs.barcode_text) or p.gtin != obs.barcode_text):
            continue
        # Entirely unreadable packages cannot reserve every expected product.
        if obs.product_name_text or obs.barcode_text:
            result.append(p.sku_id)
    complete = bool(obs.brand_text and obs.product_name_text and obs.variant_text and obs.size_text and obs.pack_count_text)
    barcode = valid_gtin(obs.barcode_text)
    resolved = len(result)==1 and (complete or barcode) and not obs.uncertain
    return result, resolved


def iou(a,b):
    if not a or not b: return 0
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return intersection/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)


def fuse(observations):
    kept=[]
    for obs in observations:
        # Different crop sightings only; adjacent copies and unlocated evidence survive.
        duplicate=next((p for p in kept if p.crop_id != obs.crop_id and not p.is_partial and not obs.is_partial and iou(p.box_2d,obs.box_2d) >= .75 and all(norm(getattr(p,k))==norm(getattr(obs,k)) for k in ('brand_text','product_name_text','variant_text','size_text','pack_count_text','barcode_text'))),None)
        if duplicate is None: kept.append(obs)
    return kept


def compare(observations, catalogue, allocations, bay_id):
    observations=fuse(observations)
    expected={a.sku_id for a in allocations if a.bay_id==bay_id}
    found=set(); review=set(); rows=[]; unresolved=[]; tasks=[]
    for obs in observations:
        ids, resolved=candidates(obs,catalogue)
        row={**obs.model_dump(),'candidate_sku_ids':ids,'matched_sku_id':ids[0] if resolved else None,'identity_status':'found' if resolved else 'review' if ids else 'unknown'}
        rows.append(row)
        if resolved:
            found.update(set(ids)&expected)
            if ids[0] not in expected:
                tasks.append(ReviewTask(task_id='placement-'+obs.instance_id,kind='placement',sku_ids=ids,instance_id=obs.instance_id,message='This product is not assigned to the selected demo bay. Check its placement.'))
        else:
            review.update(set(ids)&expected)
            unresolved.append(row)
            tasks.append(ReviewTask(task_id='identity-'+obs.instance_id,kind='identity',sku_ids=ids,instance_id=obs.instance_id,message='Read the variant, size and pack count on the package. A closer photo may help.'))
    review-=found
    missing=expected-found-review
    for sku in sorted(missing):
        tasks.append(ReviewTask(task_id='missing-'+sku,kind='not_observed',sku_ids=[sku],message='Not observed in these readings. Check the shelf before checking backroom stock.'))
    products=[{**p.model_dump(),'status':'found' if p.sku_id in found else 'review' if p.sku_id in review else 'not_observed'} for p in catalogue if p.sku_id in expected]
    # Counts are unique expected SKUs touched by unresolved evidence, not arbitrary assignments.
    visible=None if any(o.box_2d is None or o.is_partial for o in observations) else len(observations)
    return ComparisonResult(bay_id=bay_id,products=products,observations=rows,unresolved=unresolved,tasks=tasks,counts={'found':len(found),'review':len(review),'not_observed':len(missing),'expected':len(expected)},visible_instances=visible)
