# linkkipallo

Telegram bot for Linkki Jyväskylä ry.

## How to run bot and databse with Docker Compose (recommended for local development and deployment)

You can run a local Postgres instance with Docker Compose included in this repo. It creates a `db` service and a persistent volume.

1. Start the DB:
    ```bash
    docker compose up -d db
    ```

2. Wait for the DB to become healthy (the compose healthcheck uses `pg_isready`).

3. Start the bot (example dry-run):
    ```bash
    docker compose up -d bot
    ```

4.1 To stop the bot without stopping the database:
    ```bash
    docker compose stop bot
    ```

4.2 To stop and remove the Database:
    ```bash
    docker compose down -v
    ```
4.3 Run once without removing the database:
    ```bash
    docker compose run --rm bot --mode monthly
    ```

Postgres notes:
    - The bot will create a simple `events` table on startup when `DATABASE_URL` is provided.
    - The table stores a stable hash of the event payload and an optional `event_id`. The bot only posts events that have not been posted.

## How to run without docker

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


