from unittest.mock import MagicMock, patch
import pytest
import requests
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


# --- Existing 3 Baseline Tests ---

def test_index_page_with_mocked_api(client):
    mock_weather = MagicMock()
    mock_weather.raise_for_status.return_value = None
    mock_weather.json.return_value = {"current": {"temperature_2m": 26.5}}

    mock_aqi = MagicMock()
    mock_aqi.raise_for_status.return_value = None
    mock_aqi.json.return_value = {"current": {"us_aqi": 38}}

    with patch("app.requests.get", side_effect=[mock_weather, mock_aqi]):
        response = client.get("/?city=hanoi")
        assert response.status_code == 200
        assert b"26.5" in response.data
        assert b"38" in response.data


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"http_requests_total" in response.data


# --- 10 Additional Status Code & Gate Tests ---

def test_index_default_city_status_200(client):
    """Test 4: Root route without query parameters returns 200 OK."""
    with patch("app.fetch_weather_and_aqi", return_value={"city": "Ha Noi", "temp": "24°C", "aqi": "42", "source": "Mock"}):
        response = client.get("/")
        assert response.status_code == 200


@pytest.mark.parametrize("city_slug", ["hanoi", "london", "tokyo"])
def test_supported_cities_status_200(client, city_slug):
    """Tests 5, 6, 7: All configured cities return 200 OK."""
    with patch("app.fetch_weather_and_aqi", return_value={"city": city_slug, "temp": "20°C", "aqi": "30", "source": "Mock"}):
        response = client.get(f"/?city={city_slug}")
        assert response.status_code == 200


def test_unknown_city_fallback_status_200(client):
    """Test 8: Unsupported city parameter falls back gracefully with 200 OK."""
    with patch("app.fetch_weather_and_aqi", return_value={"city": "Ha Noi", "temp": "24°C", "aqi": "42", "source": "Mock"}):
        response = client.get("/?city=unknown_city_xyz")
        assert response.status_code == 200


def test_external_api_timeout_returns_200_with_fallback(client):
    """Test 9: External weather API timeout still serves dashboard with 200 OK."""
    with patch("app.requests.get", side_effect=requests.Timeout("Connection timed out")):
        response = client.get("/?city=london")
        assert response.status_code == 200
        assert b"Fallback Data" in response.data


def test_external_api_500_error_returns_200_with_fallback(client):
    """Test 10: Upstream 500 error from Open-Meteo still serves 200 OK fallback."""
    mock_error_res = MagicMock()
    mock_error_res.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

    with patch("app.requests.get", return_value=mock_error_res):
        response = client.get("/?city=tokyo")
        assert response.status_code == 200
        assert b"Fallback Data" in response.data


def test_nonexistent_route_returns_404(client):
    """Test 11: Undefined route returns standard 404 Not Found."""
    response = client.get("/api/v1/nonexistent-endpoint")
    assert response.status_code == 404


def test_post_to_health_returns_405(client):
    """Test 12: Disallowed HTTP POST method on /health returns 405 Method Not Allowed."""
    response = client.post("/health")
    assert response.status_code == 405


def test_head_request_to_health_returns_200(client):
    """Test 13: HTTP HEAD probe (used by load balancers/monitoring) returns 200 OK."""
    response = client.head("/health")
    assert response.status_code == 200