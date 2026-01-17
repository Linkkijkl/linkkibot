#!/usr/bin/env bash
# Small runner for linkki_bot
# - Loads `.env`
# - Waits for DATABASE_URL host:port to be reachable with `--wait-db`
# - Forwards any flags to `linkki_bot.py`

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$ROOT_DIR/.env" ]; then
	set -o allexport
	. "$ROOT_DIR/.env"
	set +o allexport
fi

usage() {
	cat <<EOF
Usage: $0 [--wait-db] [--modes] [--sample]

Options:
	--wait-db   Wait until DATABASE_URL host:port accepts TCP connections (useful after `docker compose up`).
	Any other flags are forwarded to linkki_bot.py (e.g. --modes, --sample).
EOF
}

WAIT_DB=0
ARGS=()
while [ "$#" -gt 0 ]; do
	case "$1" in
		--wait-db)
			WAIT_DB=1
			shift
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			ARGS+=("$1")
			shift
			;;
	esac
done

if [ "$WAIT_DB" -eq 1 ]; then
	if [ -z "${DATABASE_URL-}" ]; then
		echo "DATABASE_URL is not set; cannot wait for DB." >&2
		exit 2
	fi

	# expected format: postgres://user:pass@host:port/db
	HOSTPORT=$(printf "%s" "$DATABASE_URL" | sed -E 's#.*@([^:/]+):([0-9]+).*#\1 \2#') || true
	HOST=$(printf "%s" "$HOSTPORT" | awk '{print $1}') || true
	PORT=$(printf "%s" "$HOSTPORT" | awk '{print $2}') || true

	if [ -z "$HOST" ] || [ -z "$PORT" ]; then
		echo "Failed to parse host:port from DATABASE_URL; defaulting to localhost:5432" >&2
		HOST=localhost
		PORT=5432
	fi

	echo "Waiting for DB at $HOST:$PORT..."
	TIMEOUT=60
	START=$(date +%s)
	while :; do
		if (</dev/tcp/$HOST/$PORT) >/dev/null 2>&1; then
			echo "DB reachable at $HOST:$PORT"
			break
		fi
		NOW=$(date +%s)
		ELAPSED=$((NOW - START))
		if [ $ELAPSED -ge $TIMEOUT ]; then
			echo "Timed out waiting for DB after ${TIMEOUT}s" >&2
			exit 3
		fi
		sleep 1
	done
fi

echo "Starting bot with args: ${ARGS[*]:-}"

if [ "${#ARGS[@]}" -eq 1 ] && [[ "${ARGS[0]}" == *" "* ]]; then
	read -r -a ARGS <<<"${ARGS[0]}"
fi

exec python3 "$ROOT_DIR/linkki_bot.py" "${ARGS[@]}"
