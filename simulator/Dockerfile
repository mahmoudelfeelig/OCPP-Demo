FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements.txt
COPY requirements-dev.txt requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY simulator simulator
COPY tests tests

EXPOSE 9000

CMD ["uvicorn", "simulator.app:app", "--host", "0.0.0.0", "--port", "9000"]
