#!/usr/bin/env bash
# scripts/setup_branch_protection.sh
#
# Valza runs this ONCE after the first CI run goes green on main.
# Requires: GitHub CLI (gh) authenticated with admin rights on the repo.
#
# What it enforces on `main`:
#   - All three CI jobs must be green before merge
#   - At least 1 approving review required
#   - Stale reviews dismissed on new push
#   - No direct pushes (even from admins)
#   - Linear history (squash/rebase only — keeps git log clean)
#
# Usage:
#   gh auth login
#   bash scripts/setup_branch_protection.sh <owner> <repo>
#
# Example:
#   bash scripts/setup_branch_protection.sh desklite-org desklite

set -euo pipefail

OWNER=${1:?"Usage: $0 <owner> <repo>"}
REPO=${2:?"Usage: $0 <owner> <repo>"}

echo "→ Setting branch protection on main for ${OWNER}/${REPO}…"

gh api \
  --method PUT \
  "repos/${OWNER}/${REPO}/branches/main/protection" \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Backend (lint + tests)",
      "Frontend (lint + type-check + build)",
      "Security scan"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "allow_squash_merge": true,
  "allow_merge_commit": false,
  "allow_rebase_merge": true,
  "required_linear_history": true,
  "delete_branch_on_merge": true
}
EOF

echo "✓ Branch protection applied. Verify at:"
echo "  https://github.com/${OWNER}/${REPO}/settings/branches"
