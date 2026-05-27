FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY backend/ .

COPY frontend/ ./frontend/

RUN apt-get update && apt-get install -y --no-install-recommends \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/frontend
RUN npm install && npm run build

WORKDIR /app

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]