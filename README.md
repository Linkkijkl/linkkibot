# linkkipallo

Telegram bot for Linkki Jyväskylä ry.

## How to contribute and run

1. Create your own bot using BotFather. Go to the Telegram API pages for more info.
2. Create and activate a python venv.
3. Install requirements:
    ```bash
    pip install -r requirements.txt
    ```
4. Copy .env.example into .env and fill in the variables, or export env vars directly.

5. Run the helper script `run_bot.sh`:
    ```bash
    ./run_bot.sh --wait-db --dry-run --sample
    ```

Run using the sample_events.json
    ```bash
    python3 -m http.server 8000 &; set -x SAMPLE_URL "http://localhost:8000/sample_events.json"; ./run_bot.sh --wait-db --sample --dry-run; kill %1
    ```

Postgres notes:
    - The bot will create a simple `events` table on startup when `DATABASE_URL` is provided.
    - The table stores a stable hash of the event payload and an optional `event_id` (if present in the event). The bot only posts events that are new.


## Run Postgres with Docker Compose (recommended for local development and deployment)

You can run a local Postgres instance with Docker Compose included in this repo. It creates a `db` service and a persistent volume.

1. Start the DB:
    ```bash
    docker compose up -d
    ```

2. Wait for the DB to become healthy (the compose healthcheck uses `pg_isready`).

3. Run the bot (example dry-run):
    ```fish
    python3 linkki_bot.py --dry-run
    ```

4. To stop and remove the Database:
    ```bash
    docker compose down -v
    ```
