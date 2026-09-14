FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
# uid 1000 matches the owner of the bind-mounted ./data on alpine-docker.
RUN pip install --no-cache-dir . \
    && useradd --system --uid 1000 --no-create-home volvowatch \
    && mkdir -p /app/data \
    && chown -R volvowatch:volvowatch /app

USER volvowatch

EXPOSE 8000
VOLUME ["/app/data"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
