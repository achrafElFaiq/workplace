FROM python:3.12-slim

RUN pip install uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY portal.py config.yaml ./

EXPOSE 8500
CMD ["uv", "run", "streamlit", "run", "portal.py", "--server.port=8500", "--server.headless=true", "--server.address=0.0.0.0"]
