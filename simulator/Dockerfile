FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements.txt
COPY requirements-dev.txt requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY simulator simulator
COPY tests tests

RUN addgroup --system ocpp && adduser --system --ingroup ocpp ocpp \
    && chown -R ocpp:ocpp /app
USER ocpp

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/health', timeout=3).read()"
CMD ["uvicorn", "simulator.app:app", "--host", "0.0.0.0", "--port", "9000"]
