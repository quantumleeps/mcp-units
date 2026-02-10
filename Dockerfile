FROM python:3.12-slim

RUN pip install uv

COPY . /app
WORKDIR /app

RUN uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "fastmcp", "run", "src/mcp_units/server.py", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
