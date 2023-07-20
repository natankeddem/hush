#!/bin/bash
set -x
# Get the PUID and PGID from environment variables (or use default values 1000 if not set)
PUID=${PUID:-1000}
PGID=${PGID:-1000}

# Check if the provided PUID and PGID are non-empty, numeric values; otherwise, assign default values
if ! [[ "$PUID" =~ ^[0-9]+$ ]]; then
  PUID=1000
fi

if ! [[ "$PGID" =~ ^[0-9]+$ ]]; then
  PGID=1000
fi

# Check if the specified group with PGID exists, if not, create it
if ! getent group "$PGID" >/dev/null; then
  groupadd -g "$PGID" appgroup
fi

# Create the appuser with the provided PUID and PGID
useradd --create-home --shell /bin/bash --uid "$PUID" --gid "$PGID" appuser

# Change the ownership of the /app directory to the newly created appuser
chown -R appuser:appgroup /app

# Prepare an array to pass all environment variables to the subshell
# The array includes all environment variables except some common variables that may interfere with the subshell
declare -a env_vars=("$(env | grep -v -E '^(SHELL|PWD|SHLVL|_|OLDPWD|TERM|LANG)=' | sed 's/"/\\"/g' | awk -F "=" '{printf "%s=\"%s\" ", $1, $2}')")

# Prepare a command to run the Python program with all environment variables
python_cmd="cd /app && ${env_vars[@]} python main.py"

exec su appuser -p -c "cd /app && python main.py"
