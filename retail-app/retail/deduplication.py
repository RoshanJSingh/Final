"""Conservative cross-crop duplicate suppression; never a physical stock count."""

def overlap(a, b):
    intersection = max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection / union if union else 0


def deduplicate(products):
    kept, duplicates = [], []
    def evidence(p):
        return p.model_dump(exclude={'instance_id','crop_id','box_2d','is_partial'})
    for product in products:
        previous = next((p for p in kept if p.crop_id != product.crop_id
                         and p.box_2d and product.box_2d
                         and overlap(p.box_2d, product.box_2d) >= .8
                         and evidence(p) == evidence(product)), None)
        if previous:
            duplicates.append({'observation_id':product.instance_id,'duplicate_of':previous.instance_id,
                               'reason':'Same evidence and strongly overlapping boxes in different crops.'})
        else:
            kept.append(product)
    return kept, duplicates
