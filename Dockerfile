FROM python:3.11-slim

WORKDIR /app
COPY 02_BACKEND/requirements.txt /app/02_BACKEND/requirements.txt
RUN pip install --no-cache-dir -r /app/02_BACKEND/requirements.txt

COPY 02_BACKEND /app/02_BACKEND
COPY 03_DATABASE /app/03_DATABASE
COPY 06_SECURITY/moderation_config.example.json /app/06_SECURITY/moderation_config.example.json

ENV PYTHONPATH=/app/02_BACKEND
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
