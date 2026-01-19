FROM python:3.14
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    uv pip install --system --no-cache-dir --upgrade -r /tmp/requirements.txt

COPY ./src .

ENTRYPOINT ["python3", "linkki_bot.py"]
