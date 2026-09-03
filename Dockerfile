FROM python:3.12-slim

RUN pip install uv

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev

COPY portal.py mcp_server.py agent.py index.html start.sh ./
RUN chmod +x start.sh

ENV PORT=8501
ENV MCP_PORT=8510
EXPOSE 8501 8510
CMD ["./start.sh"]
