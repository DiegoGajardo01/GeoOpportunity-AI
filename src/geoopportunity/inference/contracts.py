"""Future-only contracts for commercial sales; no predictor is deployed."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CommercialDomain = Literal['independent_commercial_sales']


class SalesPredictionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    domain: CommercialDomain
    record_id: str = Field(min_length=1)
    features: dict[str, float] = Field(min_length=1)


class SalesPredictionResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', protected_namespaces=())

    domain: CommercialDomain
    record_id: str
    predicted_sales: float
    model_version: str
    disclaimer: Literal['Not valid for forecasting sales of Chilean coffee shops.']


class ModelInfo(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    domain: CommercialDomain = 'independent_commercial_sales'
    status: Literal['not_trained'] = 'not_trained'
    model_version: None = None
    disclaimer: str = 'Not valid for forecasting sales of Chilean coffee shops.'
