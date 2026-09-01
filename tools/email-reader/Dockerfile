FROM python:3.12-slim

RUN pip install uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8503
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8503", "--server.headless=true", "--server.address=0.0.0.0"]
