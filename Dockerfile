FROM python:3.11-slim

WORKDIR /app

# Copy dependency list first for faster layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and tests
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]