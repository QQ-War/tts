FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY python_app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY config.yaml ./config.yaml
COPY python_app/ ./python_app

EXPOSE 8000

ENV HOST=0.0.0.0 \
    PORT=8000

CMD ["uvicorn", "python_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
