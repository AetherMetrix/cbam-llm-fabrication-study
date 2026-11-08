#!/usr/bin/env bash
# =============================================================================
# research leak-scan belt — Fabricated Precision pilot public repo
# Frontend-owned PRE-PUBLISH hygiene gate (ops 02887 / 02900). FAIL-CLOSED.
# Run before EVERY public push (pre-registration push and the later results push).
#
# Scans the PUBLIC set only — everything under the pilot repo EXCEPT the
# internal-only files (SPEC.md, BUILD-STATUS.md, authoring/), compiled artifacts
# (__pycache__, *.pyc), .git, and this publish/ dir itself (so the belt's own
# pattern definitions can't self-trigger). The published set MUST equal this
# scanned set — the push runbook uses the same exclusions.
#
# Five belts, each fail-closed:
#   1. secrets            — API-key value shapes / private keys / hardcoded creds
#   2. proprietary-engine — real imports of the production engine + its symbols
#   3. section-9 names    — confidential expert names (conservative; human-cleared)
#   4. internal infra     — Lightsail, private IPs, internal hostnames
#   5. application-framing — the spec's personal-application voice (boundary #4)
#
# Canary allow-list: task `canary` strings (CANARY-<16 hex>) are INTENDED-public
# and are stripped before the secret belt so they never read as secrets (op 02900).
#
# NON-GOAL (ops 02889/02890): this belt does NOT treat model-identity names
# (claude/gpt/gemini/anthropic/openai/google) in results/ or analysis/ as findings.
# Blinding is grading-time only; the public comparison repo RE-REVEALS model
# identities post-grading for replicability. Do not add an "identity-strip" belt.
# =============================================================================
set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"   # publish/ is one level under the repo root
NEG=0
case "${1:-}" in
  --neg-test) NEG=1 ;;
  "" ) : ;;
  * ) REPO_ROOT="$1" ;;
esac

TOTAL_FILE="$(mktemp)"; echo 0 > "$TOTAL_FILE"
trap 'rm -f "$TOTAL_FILE"' EXIT
add_hits() { echo $(( $(cat "$TOTAL_FILE") + $1 )) > "$TOTAL_FILE"; }

# ---- the public scan set (== publish set) -----------------------------------
scan_paths() {
  find "$1" -type f \
    ! -path '*/.git/*' \
    ! -path '*/__pycache__/*' ! -name '*.pyc' \
    ! -path '*/authoring/*' \
    ! -path '*/publish/*' \
    ! -name 'BUILD-STATUS.md' \
    ! -name 'SPEC.md' \
    ! -name '.env' ! -name '.env.*' \
    ! -name 'GRADER_SETTINGS.json' ! -name 'MODEL_SETTINGS.json' \
    ! -name '*.key' ! -name '*.pem' \
    2>/dev/null | sort
}
# NOTE: .env*, populated *_SETTINGS.json (keys/model IDs — only *.example.json ships),
# and *.key/*.pem are INTERNAL secrets-bearing files. They are excluded from the public
# set (never published); the push manifest excludes the same. The belt does not scan them
# because they never ship. Added at the results-phase push (op 02957) after .env.research
# (a live RESEARCH_ANTHROPIC_API_KEY) + grader/GRADER_SETTINGS.json appeared in the tree.

# ---- patterns ---------------------------------------------------------------
SECRET_RE='(sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{24,}|AIza[0-9A-Za-z_-]{35}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(secret|token|password|api[_-]?key)[[:space:]]*[:=][[:space:]]*["'"'"'][A-Za-z0-9/_+-]{16,}["'"'"'])'
ENGINE_RE='(^|[^A-Za-z0-9_])(from|import)[[:space:]]+system_(engines|api)([^A-Za-z0-9_]|$)|pcf_composer|pack_content_hash|signed_assessment|SCHEDULE1_LINKED|sector_signoff|[^A-Za-z_]rule_pack[^A-Za-z_]'
NAME_RE='\b(Matt|Matthew|Chen|John|Maxwell|Sam|Samantha|Alex|Bolton|Turner|David|Zack|Crooks|Mason|Simmons)\b'
INFRA_RE='Lightsail|\b10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b|\b192\.168\.[0-9]{1,3}\.[0-9]{1,3}\b|\b172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3}\b|aethermetrix-system|\.internal\b'
APPFRAME_RE='application essay|Link [0-9]+ in (the |my )?application|in (my|the) application|temperature-zero anecdote|personal (statement|application)|my application'

# ---- one belt: $1=label $2=dir $3=regex $4=ci(i|"") $5=canary_strip(1|0) -----
belt() {
  local label="$1" dir="$2" re="$3" ci="$4" strip="$5" hits=0 f out gflag="-nE"
  [ "$ci" = "i" ] && gflag="-niE"
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ "$strip" = "1" ]; then
      out=$(sed -E 's/CANARY-[0-9A-Fa-f]{16}//g' "$f" 2>/dev/null | grep $gflag "$re" 2>/dev/null)
    else
      out=$(grep $gflag "$re" "$f" 2>/dev/null)
    fi
    if [ -n "$out" ]; then
      echo "  [$label] ${f#"$dir"/}"
      printf '%s\n' "$out" | sed 's/^/        /'
      hits=$((hits + $(printf '%s\n' "$out" | grep -c .)))
    fi
  done < <(scan_paths "$dir")
  add_hits "$hits"
}

run_all() {   # $1=dir ; runs all 5 belts, leaves the total in TOTAL_FILE
  echo 0 > "$TOTAL_FILE"
  belt secret   "$1" "$SECRET_RE"   "" 1
  belt engine   "$1" "$ENGINE_RE"   "" 0
  belt name     "$1" "$NAME_RE"     "" 0
  belt infra    "$1" "$INFRA_RE"    "" 0
  belt appframe "$1" "$APPFRAME_RE" i 0
}

# ---- neg-test: the probe must be able to fail (positive anchor + must-fire) --
if [ "$NEG" = "1" ]; then
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"; rm -f "$TOTAL_FILE"' EXIT
  mkdir -p "$tmp/ruleset"
  # CLEAN fixture (positive anchor): a canary PASSES; a benign clean-room disclaimer PASSES
  cat > "$tmp/clean.json" <<'EOF'
{ "canary": "CANARY-A35654FEE544637F",
  "note": "Clean-room: no import of system-api/ or system-engines/. Keys from RESEARCH_ANTHROPIC_API_KEY env var.",
  "producer_country": "Turkiye", "figure_tCO2e": 1850.0 }
EOF
  run_all "$tmp"; clean_hits=$(cat "$TOTAL_FILE")
  # DIRTY fixture: one planted instance of each of the 5 categories.
  # The planted secret is ASSEMBLED from parts so THIS file (which ships publicly)
  # carries no literal key-shaped string for external secret scanners to flag; the
  # temp fixture written below still holds the full shape, so the secret belt is tested.
  printf 'key = "%s"\n' "sk-""ant-""api03ABCDEFGHIJKLMNOPQRSTUV" > "$tmp/ruleset/dirty.txt"
  cat >> "$tmp/ruleset/dirty.txt" <<'EOF'
from system_engines import pcf_composer
Reviewed by Turner and Mason.
Deployed on Lightsail at 10.0.1.164
See Link 1 in application; the temperature-zero anecdote from my application.
EOF
  echo "=== NEG-TEST findings on dirty fixture ==="
  run_all "$tmp"; dirty_hits=$(cat "$TOTAL_FILE")
  echo "=== NEG-TEST result ==="
  echo "  clean fixture hits (expect 0): $clean_hits"
  echo "  dirty fixture hits (expect >=5): $dirty_hits"
  if [ "${clean_hits:-1}" -eq 0 ] && [ "${dirty_hits:-0}" -ge 5 ]; then
    echo "  PASS — silent on clean+canary+disclaimer; fires on all 5 planted leaks."
    exit 0
  fi
  echo "  FAIL — belt mis-calibrated."
  exit 2
fi

# ---- normal run -------------------------------------------------------------
echo "==> research leak-scan: scanning the public set under research/fabricated-precision-pilot"
nfiles=$(scan_paths "$REPO_ROOT" | wc -l | tr -d ' ')
echo "    $nfiles public files in scope (SPEC.md / BUILD-STATUS.md / authoring/ / __pycache__ / publish/ excluded)"
echo "----"
run_all "$REPO_ROOT"; total=$(cat "$TOTAL_FILE")
echo "----"
if [ "${total:-0}" -eq 0 ]; then
  echo "==> research leak-scan: CLEAN — 0 findings across all 5 belts."
  exit 0
fi
echo "==> research leak-scan: $total FINDING(S) — fail-closed. Resolve at source before any public push."
exit 1
