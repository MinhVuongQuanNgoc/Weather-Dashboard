import time
from flask import Flask, jsonify, render_template_string, request
from prometheus_client import Counter, Histogram, generate_latest

app = Flask(__name__)

# Metrics for monitoring requests and latency
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency"
)


@app.before_request
def before_request():
    request.start_time = time.time()


@app.after_request
def after_request(response):
    latency = time.time() - request.start_time
    REQUEST_LATENCY.observe(latency)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.path).inc()
    return response


@app.route("/")
def index():
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
            .footer { margin-top: 20px; font-size: 12px; color: #64748b; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Real-Time Weather &amp; Air Quality Dashboard</h1>
            <p>Powered by Python (Flask)</p>

            <div class="metric-box">
                <h3>City: Hanoi</h3>
                <p><strong>Temperature:</strong> 24&deg;C</p>
                <p><strong>Condition:</strong> Partly Cloudy</p>
                <p><strong>Air Quality Index (AQI):</strong> 42 (Good)</p>
            </div>

            <p style="color: #16a34a; font-weight: bold;">Status: Running Locally</p>
            <div class="footer">Local Development Environment</div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template)


@app.route("/health")
def health():
    return jsonify(status="healthy", service="weather-dashboard", runtime="python"), 200


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)