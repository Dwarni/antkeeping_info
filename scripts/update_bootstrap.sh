#!/bin/bash
# Updates Bootstrap CSS/JS and Bootstrap Icons to the specified versions.
# Downloads files directly from jsDelivr and places them in global_static/.
# After running, update the version query strings in templates/layout.html manually.

set -e

BS_VERSION="5.3.8"
BI_VERSION="1.13.1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CSS_DIR="$PROJECT_ROOT/global_static/css"
JS_DIR="$PROJECT_ROOT/global_static/js"

echo "Updating Bootstrap to v${BS_VERSION} and Bootstrap Icons to v${BI_VERSION}..."

curl -fsSL -o "$CSS_DIR/bootstrap.min.css" \
  "https://cdn.jsdelivr.net/npm/bootstrap@${BS_VERSION}/dist/css/bootstrap.min.css"
echo "  [ok] bootstrap.min.css"

curl -fsSL -o "$JS_DIR/bootstrap.bundle.min.js" \
  "https://cdn.jsdelivr.net/npm/bootstrap@${BS_VERSION}/dist/js/bootstrap.bundle.min.js"
echo "  [ok] bootstrap.bundle.min.js"

curl -fsSL -o "$CSS_DIR/bootstrap-icons.min.css" \
  "https://cdn.jsdelivr.net/npm/bootstrap-icons@${BI_VERSION}/font/bootstrap-icons.min.css"
echo "  [ok] bootstrap-icons.min.css"

echo ""
echo "Done. Now update the version strings in templates/layout.html:"
echo "  Bootstrap:       ?v=${BS_VERSION}"
echo "  Bootstrap Icons: ?v=${BI_VERSION}"
