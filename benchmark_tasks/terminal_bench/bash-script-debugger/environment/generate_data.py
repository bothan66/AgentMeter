script = '''#!/bin/bash
# Deployment script
# Usage: ./deploy.sh <config_file>

CONFIG_FILE=$1

# Bug1: wrong operator. Should be [ ! -f "$CONFIG_FILE" ].
# As written, -d checks for a DIRECTORY; a regular config file makes this
# condition false, so a missing/invalid argument is never caught.
if [ -d "$CONFIG_FILE" ]; then
    echo "Error: config file not found: $CONFIG_FILE"
    exit 1
fi

# Source the config to load environment variables
source "$CONFIG_FILE"

# Bug2: mkdir is missing the -p flag; fails when /app/deploy does not exist.
mkdir /app/deploy/releases /app/deploy/logs

# Bug3: DEPLOY_PATH is unquoted; word-splitting would break paths containing spaces.
DEPLOY_PATH="/app/deploy"
chmod 755 $DEPLOY_PATH

TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# Bug4: > truncates the log on every run; should use >> to append.
echo "$TIMESTAMP - Deployed version ${APP_VERSION:-unknown}" > /app/deploy/logs/deploy.log

# Bug5: APP_ENV is set but not exported, so python3 subprocess cannot see it.
APP_ENV="production"
python3 -c "import os, sys; sys.exit(0 if os.environ.get('APP_ENV') == 'production' else 1)"

echo "Deployment successful"
exit 0
'''
with open('/app/scripts/deploy.sh', 'w') as f:
    f.write(script)
