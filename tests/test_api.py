from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from geoopportunity.api.app import create_app
from geoopportunity.config import Settings
from geoopportunity.inference.contracts import SalesPredictionRequest, SalesPredictionResponse


def test_health_is_ready_without_any_dataset_or_model():
    client = TestClient(create_app(Settings()))
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_model_info_explicitly_reports_unavailable_commercial_model():
    client = TestClient(create_app(Settings()))
    response = client.get('/model/info')
    assert response.status_code == 200
    assert response.json() == {
        'domain': 'independent_commercial_sales',
        'status': 'not_trained',
        'model_version': None,
        'disclaimer': 'Not valid for forecasting sales of Chilean coffee shops.',
    }


def test_sales_contract_requires_commercial_domain_and_never_emits_a_prediction():
    with pytest.raises(ValidationError):
        SalesPredictionRequest.model_validate({
            'domain': 'chilean_coffee_shops', 'record_id': 'a', 'features': {'a': 1.0}
        })
    with pytest.raises(ValidationError):
        SalesPredictionResponse.model_validate({
            'domain': 'independent_commercial_sales', 'record_id': 'a',
            'predicted_sales': 10.0, 'model_version': 'v1'
        })


def test_settings_reject_invalid_log_level():
    with pytest.raises(ValidationError):
        Settings(log_level='not-a-level')
