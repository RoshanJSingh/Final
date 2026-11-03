"""Catalogue identity matching for the two-photo demo.

Use explicit equivalent wording and structured evidence, never edit distance or
bay membership. Name/variant, selling format, quantity and geometry are separate.
"""
import re
import unicodedata
from dataclasses import dataclass
from itertools import permutations

from .compare import same_size

MATCHING_VERSION = 'retail-identity-3'


def norm(value):
    value = unicodedata.normalize('NFKC', value or '').casefold()
    value = re.sub(r"[’']", '', value)
    value = re.sub(r'[^\w.]+', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


BRANDS = {
    'coca cola': {'coca cola', 'cocacola', 'coke', 'the coca cola company', 'coca cola company'},
    'monster energy': {'monster', 'monster energy', 'monster beverage', 'monster beverage corporation'},
    'kelloggs': {'kelloggs', 'kellogg', 'kellogg s'},
    'quaker': {'quaker', 'quaker oats', 'the quaker oats company'},
    'general mills': {'general mills', 'generalmills'},
    'great value': {'great value', 'greatvalue'},
}


def brand_key(value):
    value=norm(value)
    return next((brand for brand,aliases in BRANDS.items() if value in aliases),value)


def identity_text(value):
    value=norm(value)
    value=re.sub(r'\bcoca\s*cola\b|\bcoke\b', 'coca cola', value)
    value=re.sub(r'\bzero(?:\s+sugar)?\b', 'zero sugar', value)
    value=re.sub(r'\boriginal\s+taste\b|\bclassic\b', 'original', value)
    value=re.sub(r'\bmultigrain\b', 'multi grain', value)
    value=re.sub(r'\blemon\s+and\s+lime\b', 'lemon lime', value)
    # Printed measurements/counts and packaging descriptors aren't flavours.
    value=re.sub(r'\b\d+(?:\.\d+)?\s*(?:fl\s*oz|floz|oz|ml|liters?|litres?|l|g|kg)\b',' ',value)
    value=re.sub(r'\b\d+\s*(?:pack|pk|ct|count|bottles?|cans?)\b',' ',value)
    value=re.sub(r'\b(?:mini|minis|cereal|soda|soft drink|soft drinks|carbonated|beverage|drink|drinks|flavo[u]?r(?:ed)?|cartons?|boxes?|multipacks?|packs?|cans?|plastic|pet|glass|bottles?|family size|giant size|purified|drinking|water)\b',' ',value)
    return re.sub(r'\s+',' ',value).strip()


def key(value):
    # Field order and a repeated brand don't change an identity. All remaining
    # words must agree; extra flavours are never silently discarded.
    return frozenset(identity_text(value).split())


def profile(item):
    name=item['product_name']
    if name.startswith('Coca-Cola'):
        variant=identity_text(name.removeprefix('Coca-Cola'))
        return 'coca cola',variant,False
    if name.startswith('Monster Energy'):
        variant='silver' if 'silver' in name else 'original'
        return 'monster energy',variant,'silver' in name
    if name.endswith('Chex'):
        return 'chex',identity_text(name.removesuffix('Chex')),False
    if name.startswith('Cheerios') or name.endswith('Cheerios'):
        variant=identity_text(name.replace('Cheerios',''))
        return 'cheerios',variant,False
    if name.startswith('Life '): return 'life',identity_text(name[5:]),False
    if name in {'Sprite','Sprite Mini'}: return 'sprite','lemon lime',False
    if name=='Fanta Orange Mini': return 'fanta','orange',False
    if name=='Aquafina': return 'aquafina','',False
    return identity_text(name),'original',False


def variant_aliases(variant):
    aliases={key(variant)}
    if variant=='original': aliases|={key('classic'),key('original taste')}
    if variant=='lemon lime': aliases|={key('lemon and lime'),key('original')}
    if variant=='zero sugar': aliases|={key('zero'),key('zero sugar')}
    return aliases


def name_candidates(obs,catalogue):
    name=obs.product_name_text or ''
    # Brand alone cannot match all of a manufacturer's catalogue.
    if not name.strip(): return []
    parts=[name]
    if obs.variant_text: parts.append(obs.variant_text)
    if obs.brand_text: parts.append(brand_key(obs.brand_text))
    forms={key(name)}
    for length in range(2,len(parts)+1):
        for values in permutations(parts,length):
            if name in values: forms.add(key(' '.join(values)))
    candidates=[]
    for item in catalogue:
        family,variant,never_resolve=profile(item)
        observed_brand=brand_key(obs.brand_text)
        consumer_brand=key(obs.brand_text)==key(family)
        manufacturer=norm(obs.brand_text) in {'the coca cola company','coca cola company'} and family in {'sprite','fanta'}
        if obs.brand_text and observed_brand!=brand_key(item['brand']) and not consumer_brand and not manufacturer: continue
        supplied_variant=key(obs.variant_text)
        # 'Cherry cola' and 'Original Taste cola' express the same flavour as
        # Cherry/Original. The generic word cola never selects Original.
        if family=='coca cola': supplied_variant-=key('coca cola')
        if supplied_variant and supplied_variant not in variant_aliases(variant): continue
        aliases={key(item['product_name']),key(item['brand']+' '+item['product_name'])}
        # Some default product names omit the word Original in the catalogue.
        if variant=='original':
            aliases|={key(item['product_name']+' Original'),key(item['brand']+' '+item['product_name']+' Original')}
        if family=='sprite':
            aliases|={key('Sprite Lemon Lime'),key('Sprite Original'),key('Sprite Lemon Lime Soda')}
        if family=='aquafina': aliases.add(key('Aquafina Purified Drinking Water'))
        exact=bool(aliases & forms)
        generic=key(family) in forms and family in {'coca cola','monster energy','chex','cheerios','life','fanta'}
        if exact or generic:
            candidates.append((item,exact and not never_resolve))
    return candidates


def count_in(value):
    value=norm(value)
    if re.fullmatch(r'\d+',value): return int(value)
    # Accept an explicitly printed count, not net weight or a physical count
    # inferred from repeated bottles elsewhere in the crop.
    found=re.findall(r'\b(\d+)\s*(?:pack|pk|ct|count|bottles?|cans?)\b',value)
    return int(found[0]) if len(set(found))==1 else None


def evidence_count(obs):
    counts={n for n in (count_in(obs.pack_count_text),count_in(obs.package_format_text)) if n is not None}
    return (next(iter(counts)) if len(counts)==1 else None),len(counts)>1


def canonical_format(value):
    value=norm(value)
    words=set(value.split())
    if 'mini' in words or 'minis' in words: return 'mini cans'
    if 'glass' in words and words & {'pack','multipack','carrier','bottles','bottle'}: return 'glass bottle multipack'
    if words & {'plastic','pet'} and words & {'bottle','bottles'}: return 'plastic bottle'
    if words & {'water'} and words & {'case','pack','multipack'}: return 'water case'
    if words & {'can','cans'} and words & {'carton','box','case','pack','multipack','cardboard'}: return 'can carton'
    if words & {'can','cans','aluminum','aluminium'}: return 'can'
    if words & {'carton','box','cardboard'}: return 'carton'
    return None


def expected_format(item):
    pack=item['package_format'].casefold()
    if '7.5' in pack: return 'mini cans'
    if 'glass' in pack: return 'glass bottle multipack'
    return canonical_format(pack)


def size_value(value):
    value=norm(value)
    value=re.sub(r'\bfl\.\s*oz\.?', 'fl oz', value)
    found=re.findall(r'\b\d+(?:\.\d+)?\s*(?:fl\s*oz|floz|ml|l)\b',value)
    return found[0].replace('floz','fl oz') if len(found)==1 else None


def size_matches(value,expected):
    parsed=size_value(value)
    return same_size(parsed,expected) if parsed else None


def format_match(obs,item):
    expected=expected_format(item)
    raw=norm(obs.package_format_text)
    words=set(raw.split())
    got=canonical_format(raw)
    count,conflict=evidence_count(obs)
    if conflict: return False,False,'Conflicting printed pack counts.'
    required_count=10 if expected=='mini cans' else 6 if '6-bottle' in item['package_format'] else 32 if item['product_name']=='Aquafina' else None
    if required_count and count is not None and count!=required_count:
        return False,False,'Printed pack count conflicts with the catalogue selling unit.'
    if expected=='mini cans':
        size_ok=size_matches(obs.size_text,'7.5 fl oz')
        if size_ok is False: return False,False,'Printed mini-can size conflicts with the catalogue.'
        mini=bool(re.search(r'\bmini\b',norm((obs.product_name_text or '')+' '+(obs.variant_text or ''))))
        # The printed size/count can describe a mini pack even when the model
        # calls its outer package a box or can multipack.
        if got in {'carton','can carton'} and mini: got='mini cans'
        if got=='can carton' and count==10 and size_ok: got='mini cans'
        if got=='mini cans':
            return True,count==10 and size_ok is True,'Confirm the ten-can pack and printed 7.5 fl oz size.'
    if expected=='water case' and words & {'case','pack','multipack'}:
        return True,count==32,'Confirm the printed 32-bottle case count.'
    if got=='can' and count is not None and count>1: got='can carton'
    if expected=='plastic bottle' and count is not None and count>1:
        return False,False,'A bottle multipack is not a single-bottle catalogue unit.'
    if got==expected:
        if expected=='glass bottle multipack':
            packaged=bool(words & {'pack','multipack','carrier','carton','case'}) or count is not None and count>1
            return True,packaged and (required_count is None or count==required_count),'Confirm the glass selling pack and printed count.'
        return True,required_count is None or count==required_count,'Confirm the printed pack count.'
    if got is not None:
        # Carton alone doesn't identify whether a beverage carrier holds cans
        # or bottles. Don't choose a format using catalogue uniqueness.
        if got=='carton' and expected in {'can carton','glass bottle multipack','mini cans','water case'}:
            return True,False,'The outer carton does not establish its selling format.'
        return False,False,'Visible packaging conflicts with this catalogue format.'
    if words & {'bottle','bottles'} and expected not in {'plastic bottle','glass bottle multipack'}:
        return False,False,'Bottle evidence conflicts with the catalogue format.'
    return True,False,'Selling format is unreadable or incomplete.'


def identity_uncertain(obs,item):
    if not obs.uncertain: return False
    if not obs.uncertainty_reasons: return True
    for reason in obs.uncertainty_reasons:
        reason=norm(reason).replace('_',' ')
        # These attributes are not part of a catalogue product identity. A
        # missing barcode, price, or box cannot turn Cherry into an unknown name.
        if any(word in reason.split() for word in ('brand','name','variant','flavour','flavor','format','identity')): return True
        if any(word in reason.split() for word in ('barcode','gtin','price','boundary','box','position','location')): continue
        if 'size' in reason.split() and expected_format(item)!='mini cans': continue
        if any(word in reason.split() for word in ('count','quantity')):
            if expected_format(item)!='mini cans' and '6-bottle' not in item['package_format'] and item['product_name']!='Aquafina': continue
        return True
    return False


@dataclass
class IdentityMatch:
    candidates: list
    resolved: bool
    reasons: list


def match_identity(obs,catalogue):
    names=name_candidates(obs,catalogue)
    compatible=[]; reasons=[]; complete={}
    for item,name_complete in names:
        allowed,format_complete,reason=format_match(obs,item)
        if not allowed: continue
        compatible.append(item)
        complete[item['sku']]=name_complete and format_complete and not identity_uncertain(obs,item)
        if not name_complete: reasons.append('Product variant needs confirmation; the brand alone does not establish Original.')
        if not format_complete: reasons.append(reason)
        if identity_uncertain(obs,item): reasons.extend(obs.uncertainty_reasons or ['Product identity is uncertain.'])
    resolved=len(compatible)==1 and complete[compatible[0]['sku']]
    if not compatible: reasons=['No compatible name, variant and selling-format combination in the demo catalogue.']
    elif len(compatible)>1: reasons.append('Several catalogue identities remain possible; none was selected by guessing.')
    return IdentityMatch(compatible,resolved,list(dict.fromkeys(reasons)))
