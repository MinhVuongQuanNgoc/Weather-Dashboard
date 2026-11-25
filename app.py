import time
from flask import Flask, jsonify, render_template_string, request
import requests
from prometheus_client import Counter, Histogram, generate_latest

app = Flask(__name__)

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency"
)

CITIES = {
    "hanoi": {"name": "Ha Noi", "lat": 21.0285, "lon": 105.8542},
    "london": {"name": "London", "lat": 51.5072, "lon": -0.1276},
    "tokyo": {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503},
}


@app.before_request
def before_request():
    request.start_time = time.time()


@app.after_request
def after_request(response):
    latency = time.time() - request.start_time
    REQUEST_LATENCY.observe(latency)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.path).inc()
    return response


def fetch_weather_and_aqi(city_key: str):
    city = CITIES.get(city_key.lower(), CITIES["hanoi"])
    try:
        weather_res = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": city["lat"],
                "longitude": city["lon"],
                "current": "temperature_2m,weather_code",
            },
            timeout=5,
        )
        weather_res.raise_for_status()
        temp = weather_res.json().get("current", {}).get("temperature_2m", "N/A")

        aqi_res = requests.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={
                "latitude": city["lat"],
                "longitude": city["lon"],
                "current": "us_aqi",
            },
            timeout=5,
        )
        aqi_res.raise_for_status()
        aqi = aqi_res.json().get("current", {}).get("us_aqi", "N/A")

        return {
            "city": city["name"],
            "temp": f"{temp}°C" if temp != "N/A" else "Unavailable",
            "aqi": f"{aqi} (US AQI)" if aqi != "N/A" else "Unavailable",
            "source": "Live Open-Meteo API",
        }
    except requests.RequestException:
        return {
            "city": city["name"],
            "temp": "24°C",
            "aqi": "42 (Good)",
            "source": "Fallback Data (Offline / API Timeout)",
        }


@app.route("/")
def index():
    city_param = request.args.get("city", "hanoi")
    data = fetch_weather_and_aqi(city_param)

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>DevOps Python Weather Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f0f2f5; padding: 40px; color: #333; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1 { color: #0284c7; font-size: 24px; }
            .metric-box { background: #f8fafc; border-left: 4px solid #0284c7; padding: 15px; margin: 15px 0; border-radius: 4px; }
            .links a { margin-right: 12px; color: #0284c7; text-decoration: none; font-weight: bold; }
            .footer { margin-top: 20px; font-size: 12px; color: #64748b; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Real-Time Weather &amp; Air Quality Dashboard</h1>
            <p>Powered by Python (Flask) &amp; Automated DevOps Pipeline</p>
            <div class="links">
                <a href="/?city=hanoi">Ha Noi</a>
                <a href="/?city=london">London</a>
                <a href="/?city=tokyo">Tokyo</a>
            </div>
            <div class="metric-box">
                <h3>City: {{ data.city }}</h3>
                <p><strong>Temperature:</strong> {{ data.temp }}</p>
                <p><strong>Air Quality Index:</strong> {{ data.aqi }}</p>
                <p><strong>Data Source:</strong> {{ data.source }}</p>
            </div>
            <div class="footer">DevOps Pipeline Application</div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, data=data)


@app.route("/health")
def health():
    return jsonify(status="healthy", service="weather-dashboard", runtime="python"), 200


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)