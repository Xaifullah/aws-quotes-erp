#!/usr/bin/env bash
# Sets up the quotes scraper on a fresh Ubuntu 22.04/24.04 EC2 instance.
# Idempotent: safe to re-run (it also works as the "update" script).
#
#   curl -fsSL https://raw.githubusercontent.com/Xaifullah/aws-quotes-erp/main/deploy/ec2-ubuntu/install.sh -o install.sh
#   sudo bash install.sh [branch]
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Xaifullah/aws-quotes-erp.git}"
BRANCH="${1:-${BRANCH:-main}}"
APP_DIR=/opt/quotes-erp
APP_USER=quotes
ENV_FILE=/etc/quotes-scraper.env

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash $0 [branch]" >&2
  exit 1
fi

echo "==> Installing system packages"
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip git postgresql-client

echo "==> Creating service user '$APP_USER'"
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"

echo "==> Fetching code ($BRANCH) into $APP_DIR"
if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" fetch --prune origin
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

echo "==> Creating virtualenv and installing scraper dependencies"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/scraper/requirements.txt"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> Installing environment file"
if [[ ! -f "$ENV_FILE" ]]; then
  install -m 0640 -o root -g "$APP_USER" "$APP_DIR/deploy/ec2-ubuntu/scraper.env.example" "$ENV_FILE"
  echo "    Created $ENV_FILE from the example — edit QUEUE_URL before enabling the timer."
else
  echo "    $ENV_FILE already exists, leaving it untouched."
fi

echo "==> Installing systemd units"
install -m 0644 "$APP_DIR/deploy/ec2-ubuntu/quotes-scraper.service" /etc/systemd/system/quotes-scraper.service
install -m 0644 "$APP_DIR/deploy/ec2-ubuntu/quotes-scraper.timer" /etc/systemd/system/quotes-scraper.timer
systemctl daemon-reload

cat <<MSG

Done. Next steps:
  1. sudo nano $ENV_FILE                      # set QUEUE_URL
  2. sudo systemctl start quotes-scraper.service  # one manual run
  3. journalctl -u quotes-scraper -n 50 --no-pager
  4. sudo systemctl enable --now quotes-scraper.timer
MSG
