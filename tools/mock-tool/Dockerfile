FROM python:3.12-slim

RUN pip install uv

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev

COPY . .

ENV PORT=8501
EXPOSE 8501
CMD ["uv", "run", "python", "app.py"]
