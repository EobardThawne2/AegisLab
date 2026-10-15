FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/
WORKDIR /app
ENV UV_CACHE_DIR=/tmp/uv-cache UV_NO_CACHE=1 UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock .python-version ./
RUN uv venv .venv && uv sync --locked --no-dev
COPY aegislab ./aegislab
COPY fixtures ./fixtures
RUN useradd --uid 10001 --create-home aegislab && mkdir -p /app/local-data && chown 10001:10001 /app/local-data
USER 10001:10001
EXPOSE 8000
CMD ["uv", "run", "--locked", "--no-sync", "uvicorn", "aegislab.main:app", "--host", "0.0.0.0", "--port", "8000"]
