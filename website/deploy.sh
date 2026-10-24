#!/bin/bash
# AD Labs — One-command deploy to Vercel
# Run this after `vercel login` has completed (email confirmed)

set -e
cd "$(dirname "$0")"

echo "▸ Building production bundle..."
npm run build

echo "▸ Deploying to Vercel..."
if [ -f .vercel/project.json ]; then
  # Project already linked — deploy to production
  vercel deploy --prod --yes
else
  # First deploy — link + deploy
  echo "adlabs" | vercel deploy --prod --yes --name adlabs
fi

echo ""
echo "✓ Live. Next steps:"
echo "  1. Add custom domain adlabs.in in the Vercel dashboard:"
echo "     https://vercel.com/dashboard → adlabs → Settings → Domains"
echo "  2. Point DNS: A record 76.76.21.21 (apex) or CNAME cname.vercel-dns.com (www)"
echo ""
