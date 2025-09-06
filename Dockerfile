# Build container
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder

RUN apk add git

# Change the working directory to the `app` directory
WORKDIR /app

# Copy pyproject.toml and lock file
ADD uv.lock /app
ADD pyproject.toml /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-editable

# Copy the project into the image
ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable

# Runtime container
FROM python:3.13-alpine

# Copy the environment, but not the source code
COPY --from=builder /app/.venv /app/.venv

# Run the application
EXPOSE 8000
CMD ["/app/.venv/bin/netbox-pdns"]