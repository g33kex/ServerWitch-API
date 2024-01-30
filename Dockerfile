# Builder image
FROM python:3.11.5-slim-bookworm as builder

# Install poetry
RUN pip install poetry

# Copy source
RUN mkdir -p /app
COPY pyproject.toml poetry.toml README.md /app/
COPY src/ /app/src/

# Build project
WORKDIR /app
RUN poetry install

# Base image
FROM python:3.11.5-slim-bookworm as base

COPY --from=builder /app /app

WORKDIR /app
ENV PATH="/app/.venv/bin/:$PATH"
CMD ["hypercorn", "--bind", "0.0.0.0:8000", "serverwitch_api:app"]

EXPOSE 8000
