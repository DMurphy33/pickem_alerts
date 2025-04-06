FROM ghcr.io/astral-sh/uv:debian

COPY . /app

WORKDIR /app

RUN uv sync

CMD ["uv", "run", "main.py"]
