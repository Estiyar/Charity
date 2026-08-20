FROM python:3.12-slim

ARG SERVICE_DIR
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev && rm -rf /var/lib/apt/lists/*

COPY packages/ekomek_common /packages/ekomek_common
RUN pip install --no-cache-dir /packages/ekomek_common

COPY ${SERVICE_DIR}/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ${SERVICE_DIR} /app
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
