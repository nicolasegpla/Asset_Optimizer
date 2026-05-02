FROM python:3.12-slim

# Install system libraries for AVIF support via pillow-avif-plugin
# and common image processing dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libaom-dev \
    && rm -rf /var/lib/apt/lists /tmp/* /var/tmp/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
