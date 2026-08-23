#!/usr/bin/env bash
# Install the assistant's diary tools on gs-vm.
#
#   bash assistant/install.sh
#
# Creates its own virtualenv so nothing touches the system Python the
# services run on, drops the scripts into ~/gs-app/scripts, and puts three
# commands on PATH: gs-agenda, gs-diary, gs-remind.

set -euo pipefail

APP_DIR="${GS_APP_DIR:-$HOME/gs-app}"
VENV="$APP_DIR/.venv-assistant"
BIN_DIR="$HOME/.local/bin"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/scripts" && pwd)"

echo "==> installing into $APP_DIR"
mkdir -p "$APP_DIR/scripts" "$BIN_DIR"

if [ ! -d "$VENV" ]; then
  echo "==> creating virtualenv"
  python3 -m venv "$VENV"
fi

echo "==> installing Google API libraries"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet \
  google-api-python-client google-auth google-auth-oauthlib

echo "==> copying scripts"
for script in timeparse.py gs_google.py calendar_add.py remind.py agenda.py; do
  install -m 0755 "$SRC/$script" "$APP_DIR/scripts/$script"
done

echo "==> creating commands"
make_wrapper() {
  local name="$1" script="$2"
  cat > "$BIN_DIR/$name" <<WRAPPER
#!/usr/bin/env bash
exec "$VENV/bin/python" "$APP_DIR/scripts/$script" "\$@"
WRAPPER
  chmod +x "$BIN_DIR/$name"
  echo "    $BIN_DIR/$name"
}

make_wrapper gs-diary  calendar_add.py
make_wrapper gs-remind remind.py
make_wrapper gs-agenda agenda.py

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "    NOTE: add $BIN_DIR to PATH (it is not on it right now)" ;;
esac

echo
echo "==> checking Google credentials"
if "$VENV/bin/python" "$APP_DIR/scripts/gs_google.py"; then
  echo
  echo "Done. Try:  gs-agenda --days 7"
else
  echo
  echo "Scripts are installed but Calendar is not authorised yet."
  echo "Fix that with:  $VENV/bin/python $APP_DIR/scripts/gs_google.py --authorise"
fi
