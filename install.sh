#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/claw" <<'WRAPPER'
#!/usr/bin/env bash
exec python3 /Users/davide/Tools/claw-tools/claw/cli.py "$@"
WRAPPER
chmod +x "$HOME/.local/bin/claw"
echo "$HOME/.local/bin/claw"
