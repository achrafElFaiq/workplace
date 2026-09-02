FROM python:3.12-slim

RUN pip install uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY portal.py config.yaml ./
COPY .streamlit .streamlit

EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "portal.py", "--server.port=8501", "--server.headless=true", "--server.address=0.0.0.0"]
