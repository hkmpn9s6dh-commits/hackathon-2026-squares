#!/usr/bin/env bash
# The whole result, in one run. See README.md.
set -euo pipefail
cd "$(dirname "$0")/.."
py -3 scripts/parse_record.py
py -3 scripts/solve.py
py -3 scripts/audit.py
py -3 scripts/build_report.py
py -3 scripts/build_site.py
py -3 harness/verify.py
