# linkkipallo

Telegram bot for Linkki Jyväskylä ry.


## How to run bot and database with Docker Compose (recommended for local development and deployment)

Docker Compose runs Postgres as the `eventdb` service with a persistent volume, and the bot as the `bot` service.

1. Setup:
    - Copy `.env.example` into `.env` and fill in the variables. Inside Compose the database host is `eventdb`, e.g. `DATABASE_URL="postgres://linkkari:<password>@eventdb:5432/eventdb"`.
    - Create `postgres-passwd.txt` containing the database password and `telegram-apikey.txt` containing the bot token. Both are gitignored.

2. Start the DB and wait for it to become healthy (the compose healthcheck uses `pg_isready`):
    ```bash
    docker compose up -d --wait eventdb
    ```

3. Start the bot:
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
    docker compose run --rm bot --modes post_events month
    ```


## Modes

`--modes` takes one or more of:

- `poll_events`: fetch events from `EVENTS_URL`, save the new ones and post each of them as "Uusi tapahtuma!!".
- `post_events` with `day`, `week` or `month`: poll first, then post a summary of the saved events starting between now and the end of the day, week or month.
- `dry-run`: print the messages instead of sending them.

`--sample` fetches events from `SAMPLE_URL` instead of `EVENTS_URL`.

Without `poll_events` or `post_events` the bot only creates the database tables. This is the case for `--modes month`, the default command in `docker-compose.yml`.


## Database

- The bot creates the `events` table on startup. Existing tables are not altered, so after a schema change reset the local database with `docker compose down -v`.
- Each event is stored with its JSON payload, a hash of the payload, an optional `event_id` (the event's `id`, `event_id` or `url`) and its start time. The bot only posts events that have not been saved before with a new `event_id` and payload.
- The start time is read from `start_iso8601`, or from `date` as ISO (`2026-09-30`) or `DD/MM/YYYY`. Events without a readable date are saved, but never included in the day, week or month summaries.


## How to run without docker

1. Create your own bot using BotFather. Go to the Telegram API pages for more info.
2. Create and activate a python venv.
3. Install requirements:
    ```bash
    pip install -r requirements.txt
    ```
4. Start Postgres, for example the Compose database (needs `postgres-passwd.txt`), which listens on `localhost:5432`:
    ```bash
    docker compose up -d --wait eventdb
    ```
5. Export the variables from `.env.example`, the `.env` file is only read by Docker Compose:
    ```bash
    export TELEGRAM_BOT_TOKEN="your_bot_token_here"
    export TELEGRAM_CHAT_ID="your_chat_id_here"
    export EVENTS_URL="https://example.com/events.json"
    export DATABASE_URL="postgres://linkkari:$(cat postgres-passwd.txt)@localhost:5432/eventdb"
    ```
6. Run the bot:
    ```bash
    python3 src/linkki_bot.py --modes post_events month
    ```

### Test with sample_events.json without sending messages

`sample_events.json` contains events for September 2026, and two `Testi:` events with a broken and a missing date. Update the dates to see events in the summaries.

```bash
python3 -m http.server 8000 --bind 127.0.0.1 &
export SAMPLE_URL="http://127.0.0.1:8000/sample_events.json"
unset TELEGRAM_BOT_TOKEN  # nothing can be sent even by mistake
python3 src/linkki_bot.py --sample --modes poll_events dry-run
python3 src/linkki_bot.py --sample --modes post_events month dry-run
kill %1
```

Run `docker compose down -v` to start over with an empty database.
