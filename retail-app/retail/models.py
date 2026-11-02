from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Versioned(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['1.0'] = '1.0'


class ProductObservation(Versioned):
    instance_id: str
    crop_id: str = 'full'
    brand_text: str | None = None
    product_name_text: str | None = None
    variant_text: str | None = None
    size_text: str | None = None
    pack_count_text: str | None = None
    barcode_text: str | None = None
    package_format_text: str | None = None
    visible_text: str = ''
    box_2d: list[int] | None = None
    is_partial: bool = False
    uncertain: bool = False
    uncertainty_reasons: list[str] = Field(default_factory=list)

    @field_validator('box_2d')
    @classmethod
    def box(cls, value):
        if value is not None and (len(value) != 4 or any(type(x) is not int or not 0 <= x <= 1000 for x in value) or value[0] >= value[2] or value[1] >= value[3]):
            raise ValueError('Expected positive yxyx box in 0–1000 coordinates')
        return value


class ProductMaster(Versioned):
    sku_id: str
    brand: str
    name: str
    variant: str
    size: str
    pack_count: int = Field(ge=1)
    gtin: str | None = None
    aliases: list[dict] = Field(default_factory=list)
    reference_images: list[dict] = Field(default_factory=list)
    data_mode: Literal['simulated', 'permissioned_pilot'] = 'simulated'


class ShelfAllocation(Versioned):
    allocation_id: str
    store: str = 'Demo store'
    bay_id: str
    sku_id: str
    effective_version: str = 'demo-1'
    row: int | None = None
    slot: int | None = None
    expected_facings: int | None = None


class ShelfLabel(Versioned):
    label_id: str
    visible_text: str
    price_text: str | None = None
    currency_text: str | None = None
    promotion_text: str | None = None
    box_2d: list[int] | None = None
    uncertain: bool = True
    uncertainty_reasons: list[str] = Field(default_factory=list)
    _validate_box = field_validator('box_2d')(ProductObservation.box.__func__)


class Extraction(Versioned):
    coordinate_system: Literal['yxyx_1000'] = 'yxyx_1000'
    products: list[ProductObservation] = Field(max_length=1000)
    labels: list[ShelfLabel] = Field(max_length=1000)


class ReviewTask(Versioned):
    task_id: str
    kind: Literal['identity', 'not_observed', 'placement']
    sku_ids: list[str]
    message: str
    instance_id: str | None = None


class ComparisonResult(Versioned):
    catalogue_version: str = 'demo-1'
    matching_version: str = 'retail-1'
    bay_id: str
    data_mode: str = 'simulated'
    products: list[dict]
    observations: list[dict]
    unresolved: list[dict]
    tasks: list[ReviewTask]
    counts: dict[str, int]
    visible_instances: int | None
    slot_compliance: None = None
