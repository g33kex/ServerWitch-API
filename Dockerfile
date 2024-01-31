# Builder image
FROM python:3.11.5-slim-bookworm as builder

# Install poetry
RUN pip install poetry

# Copy source
RUN mkdir -p /app
COPY pyproject.toml poetry.toml README.md hypercorn.toml logging.toml /app/
COPY src/ /app/src/

# Build project
WORKDIR /app
RUN poetry install

# Base image
FROM python:3.11.5-slim-bookworm as base

RUN mkdir -p /var/log/serverwitch
COPY --from=builder /app /app

WORKDIR /app
ENV PATH="/app/.venv/bin/:$PATH"
CMD ["hypercorn", "--config", "hypercorn.toml", "serverwitch_api:app"]

EXPOSE 8000
