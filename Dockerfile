FROM python:3.12.10-slim
WORKDIR /app
COPY requirements-railway.txt .
RUN pip install --no-cache-dir -r requirements-railway.txt
COPY backend/ backend/
COPY webapp/ webapp/
COPY data/features/ data/features/
RUN useradd -r -s /bin/false appuser && chown -R appuser:appuser /app
USER appuser
ENV PYTHONPATH=.
CMD ["python", "webapp/main.py"]
