#!/usr/bin/env bash
# Print the CHANGELOG.md section of a version, without its heading:
# everything between "## <version> ..." and the next "## ".
#
#     .github/scripts/release_notes.sh 1.0.14
set -euo pipefail
awk -v version="$1" '
  /^## / { if (found) exit; if ($2 == version) { found = 1; next } }
  found
' "$(dirname "$0")/../../CHANGELOG.md"
