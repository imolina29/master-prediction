FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY webapp/ webapp/

ENV PYTHONPATH=.

EXPOSE 8080

CMD ["python", "webapp/main.py"]
