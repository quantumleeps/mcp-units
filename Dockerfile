FROM python:3.12-slim

RUN pip install uv

RUN useradd -m -u 1000 appuser

COPY --chown=appuser:appuser . /app
WORKDIR /app

USER appuser

RUN uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "python", "-c", "from mcp_units.server import mcp; mcp.run(transport='streamable-http', host='0.0.0.0', port=8000)"]
