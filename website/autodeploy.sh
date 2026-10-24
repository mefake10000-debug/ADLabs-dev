#!/bin/bash
# Auto-deploy watcher: polls for Vercel auth, deploys the moment it completes
# Trigger: user authorizes at https://vercel.com/oauth/device?user_code=KNDT-LSLM

cd "$(dirname "$0")"
LOG=/tmp/adlabs-autodeploy.log
echo "$(date) — watcher started, polling for Vercel auth every 30s..." > "$LOG"

for i in $(seq 1 480); do  # runs up to 4 hours
  WHO=$(vercel whoami 2>&1 | tail -1)
  if [[ "$WHO" != *"Logged out"* && "$WHO" != *"error"* && "$WHO" != *"Error"* && -n "$WHO" ]]; then
    echo "$(date) — authenticated as: $WHO" >> "$LOG"
    echo "$(date) — building + deploying to production..." >> "$LOG"
    npm run build >> "$LOG" 2>&1
    echo "adlabs" | vercel deploy --prod --yes --name adlabs >> "$LOG" 2>&1
    STATUS=$?
    echo "$(date) — deploy exit code: $STATUS" >> "$LOG"
    if [ $STATUS -eq 0 ]; then
      echo "$(date) — DEPLOYED SUCCESSFULLY" >> "$LOG"
    fi
    exit $STATUS
  fi
  sleep 30
done
echo "$(date) — watcher expired after 4 hours without auth" >> "$LOG"
