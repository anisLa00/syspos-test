FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /data
ENV SYSPOS_DB_PATH=/data/syspos.db

EXPOSE 8000
CMD ["sh", "-c", "python database.py && exec python -m uvicorn main:app --host 0.0.0.0 --port 8000"]