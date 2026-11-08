#!/usr/bin/env bash
# =============================================================================
# research leak-scan belt — Fabricated Precision pilot public repo
# PRE-PUBLISH hygiene gate. FAIL-CLOSED. Run before EVERY public push.
#
# WHAT SHIPS PUBLICLY (this file): only GENERIC detection patterns —
#   1. secrets        — API-key value shapes / private keys / hardcoded creds
#   2. application-framing — personal-application voice (pilot boundary #4)
#   3. internal-IP    — RFC1918 private IP ranges (generic; no specific address)
# plus the canary allow-list and the scan runbook. This file contains NO
# confidential literals (no real names, no specific IP/host, no proprietary
# module or internal agent-role tokens) — a replicator can read every line.
#
# ORG-SPECIFIC LISTS ARE PRIVATE. The real detection lists (confidential
# collaborator names, internal topology specifics, proprietary engine symbols,
# internal multi-agent role tokens) live in `publish/leak-scan.private.sh`,
# which is gitignored, excluded from the publish set, and never shipped. An
# INTERNAL run sources it and additionally runs the private belts + a self-check
# that audits THIS file and the manifest for any confidential literal. A public
# replicator who does not have that file still gets the generic belts and loses
# nothing they need to reproduce the study. (Belt sanitized: org-specific lists kept private.)
#
# ★ The belt now scans ITSELF (self-check, internal runs) so a confidential
# literal introduced into this file or PUBLISH.md fails the scan — closing the
# audit gap that previously let the belt accumulate real names/IP/role tokens.
#
# Canary allow-list: task `canary` strings (CANARY-<16 hex>) are INTENDED-public
# and are stripped before the secret belt so they never read as secrets.
#
# NON-GOAL: this belt does NOT treat model-identity names (claude/gpt/gemini/
# anthropic/openai/google) in results/analysis as findings. Blinding is grading-
# time only; the public repo RE-REVEALS identities post-grading for replicability.
# =============================================================================
set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"   # publish/ is one level under the repo root
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
NEG=0
case "${1:-}" in
  --neg-test) NEG=1 ;;
  "" ) : ;;
  * ) REPO_ROOT="$1" ;;
esac

# ---- source the PRIVATE org-specific lists if present (internal runs only) ---
# Public replicators won't have this file; the generic belts below still run.
HAVE_PRIV=0
PRIV_CONF="$SELF_DIR/leak-scan.private.sh"
if [ -f "$PRIV_CONF" ]; then
  # shellcheck disable=SC1090
  . "$PRIV_CONF" && HAVE_PRIV=1
fi

TOTAL_FILE="$(mktemp)"; echo 0 > "$TOTAL_FILE"
trap 'rm -f "$TOTAL_FILE"' EXIT
add_hits() { echo $(( $(cat "$TOTAL_FILE") + $1 )) > "$TOTAL_FILE"; }

# ---- the public scan set (== publish set) -----------------------------------
scan_paths() {
  find "$1" -type f \
    ! -path '*/.git/*' \
    ! -path '*/__pycache__/*' ! -name '*.pyc' \
    ! -path '*/authoring/*' \
    ! -path '*/writeup/*' \
    ! -path '*/publish/*' \
    ! -name '*.private.sh' \
    ! -name 'BUILD-STATUS.md' \
    ! -name 'SPEC.md' \
    ! -name '.env' ! -name '.env.*' \
    ! -name 'GRADER_SETTINGS.json' ! -name 'MODEL_SETTINGS.json' \
    ! -name '*.key' ! -name '*.pem' \
    2>/dev/null | sort
}
# NOTE: .env*, populated *_SETTINGS.json, *.key/*.pem, and *.private.sh are
# INTERNAL secrets-bearing files — excluded from the public set (never published);
# the push manifest excludes the same. publish/ is excluded from the generic scan
# (it holds the patterns + runbook); the internal self-check audits it separately.

# ---- GENERIC patterns (PUBLIC — contain no confidential literal) -------------
SECRET_RE='(sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{24,}|AIza[0-9A-Za-z_-]{35}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(secret|token|password|api[_-]?key)[[:space:]]*[:=][[:space:]]*["'"'"'][A-Za-z0-9/_+-]{16,}["'"'"'])'
APPFRAME_RE='application essay|Link [0-9]+ in (the |my )?application|in (my|the) application|temperature-zero anecdote|personal (statement|application)|my application'
# Generic internal-IP hygiene: RFC1918 private ranges (every org uses these).
# No specific address appears here; the specific internal IP is in the private list.
IP_RE='\b10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b|\b192\.168\.[0-9]{1,3}\.[0-9]{1,3}\b|\b172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3}\b'

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

# internal-process belt (PRIVATE patterns; only runs when the private config is sourced):
# unconditional role/handoff tokens, plus the api/engines role tokens only OUTSIDE a
# clean-room-disclaimer line (so a legitimate "no import of …" disclaimer passes, while an
# authorship/handoff comment fails). The actual tokens live in the private config, not here.
belt_internal() {
  local dir="$1" hits=0 f out
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    out=$( { grep -nE "$PRIV_INTERNAL_UNCOND_RE" "$f" 2>/dev/null
             grep -nE "$PRIV_INTERNAL_APIENG_RE" "$f" 2>/dev/null | grep -viE 'import|clean-room'; } | sort -u )
    if [ -n "$out" ]; then
      echo "  [internal] ${f#"$dir"/}"
      printf '%s\n' "$out" | sed 's/^/        /'
      hits=$((hits + $(printf '%s\n' "$out" | grep -c .)))
    fi
  done < <(scan_paths "$dir")
  add_hits "$hits"
}

run_all() {   # $1=dir ; generic belts always; private belts only if the private config is present
  echo 0 > "$TOTAL_FILE"
  belt secret   "$1" "$SECRET_RE"   "" 1
  belt appframe "$1" "$APPFRAME_RE" i 0
  belt infra-ip "$1" "$IP_RE"       "" 0
  if [ "$HAVE_PRIV" = "1" ]; then
    belt name   "$1" "$PRIV_NAME_RE"   "" 0
    belt engine "$1" "$PRIV_ENGINE_RE" "" 0
    belt infra  "$1" "$PRIV_INFRA_RE"  "" 0
    belt opref  "$1" "$PRIV_OPREF_RE"  "" 0
    belt_internal "$1"
  fi
}

# ---- self-check (internal runs): audit the belt + manifest for confidential literals.
# This is the root-cause fix: publish/ is excluded from the generic scan, so without
# this the belt's own contents were never audited. We grep the PUBLIC publish/ files
# with the PRIVATE patterns only (not the generic ones — those legitimately contain
# their own pattern text), so any real name / IP / host / engine-symbol / role token
# that creeps into this file or PUBLISH.md fails the scan.
self_check() {
  [ "$HAVE_PRIV" = "1" ] || return 0
  local hits=0 rel f out
  for rel in leak-scan.sh PUBLISH.md; do
    f="$SELF_DIR/$rel"; [ -f "$f" ] || continue
    out=$( { grep -nE "$PRIV_NAME_RE"            "$f" 2>/dev/null
             grep -nE "$PRIV_INFRA_RE"           "$f" 2>/dev/null
             grep -nE "$PRIV_ENGINE_RE"          "$f" 2>/dev/null
             grep -nE "$PRIV_OPREF_RE"           "$f" 2>/dev/null
             grep -nE "$PRIV_INTERNAL_UNCOND_RE" "$f" 2>/dev/null
             grep -nE "$PRIV_INTERNAL_APIENG_RE" "$f" 2>/dev/null | grep -viE 'import|clean-room'; } | sort -u )
    if [ -n "$out" ]; then
      echo "  [self-check] publish/$rel contains confidential literal(s):"
      printf '%s\n' "$out" | sed 's/^/        /'
      hits=$((hits + $(printf '%s\n' "$out" | grep -c .)))
    fi
  done
  add_hits "$hits"
}

# ---- neg-test: the probe must be able to fail (positive anchor + must-fire) --
if [ "$NEG" = "1" ]; then
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"; rm -f "$TOTAL_FILE"' EXIT
  mkdir -p "$tmp/ruleset"
  # CLEAN fixture (positive anchor): a canary PASSES; a benign clean-room disclaimer PASSES.
  # The disclaimer line (which legitimately names the api/engines role tokens inside a
  # "no import of" context) comes from the private config so no such literal ships here.
  {
    echo '{ "canary": "CANARY-A35654FEE544637F",'
    echo '  "producer_country": "Turkiye", "figure_tCO2e": 1850.0,'
    if [ "$HAVE_PRIV" = "1" ]; then
      printf '  "note": "%s Keys from RESEARCH_ANTHROPIC_API_KEY env var." }\n' "$PRIV_CLEAN_LINE"
    else
      echo '  "note": "Keys from RESEARCH_ANTHROPIC_API_KEY env var." }'
    fi
  } > "$tmp/clean.json"
  run_all "$tmp"; clean_hits=$(cat "$TOTAL_FILE")

  # DIRTY fixture: plant one instance of each GENERIC category. The secret is ASSEMBLED
  # from parts so THIS file ships no literal key-shape; the written fixture holds the full
  # shape. The internal-IP uses a generic RFC1918 example (10.0.0.1 — not any real host).
  printf 'key = "%s"\n' "sk-""ant-""api03ABCDEFGHIJKLMNOPQRSTUV" > "$tmp/ruleset/dirty.txt"
  cat >> "$tmp/ruleset/dirty.txt" <<'EOF'
See Link 1 in application; the temperature-zero anecdote from my application.
Example internal host at 10.0.0.1 (generic RFC1918).
EOF
  # The confidential-category planted lines (real-shaped names/host/engine/role) come from
  # the PRIVATE config so no such literal is written into this public file.
  if [ "$HAVE_PRIV" = "1" ]; then
    printf '%s\n' "$PRIV_NEG_LINES" >> "$tmp/ruleset/dirty.txt"
  fi
  echo "=== NEG-TEST findings on dirty fixture ==="
  run_all "$tmp"; dirty_hits=$(cat "$TOTAL_FILE")

  # expected minimum: 3 generic (secret + appframe + infra-ip); +5 private categories when sourced
  # (name, engine, infra, op-ref, internal)
  if [ "$HAVE_PRIV" = "1" ]; then min_dirty=8; mode="private config sourced → generic + private belts"; else min_dirty=3; mode="PUBLIC-ONLY (no private config) → generic belts only"; fi
  echo "=== NEG-TEST result ($mode) ==="
  echo "  clean fixture hits (expect 0): $clean_hits"
  echo "  dirty fixture hits (expect >=$min_dirty): $dirty_hits"
  if [ "${clean_hits:-1}" -eq 0 ] && [ "${dirty_hits:-0}" -ge "$min_dirty" ]; then
    echo "  PASS — silent on clean+canary+disclaimer; fires on every planted leak."
    exit 0
  fi
  echo "  FAIL — belt mis-calibrated."
  exit 2
fi

# ---- normal run -------------------------------------------------------------
echo "==> research leak-scan: scanning the public set under research/fabricated-precision-pilot"
nfiles=$(scan_paths "$REPO_ROOT" | wc -l | tr -d ' ')
if [ "$HAVE_PRIV" = "1" ]; then
  echo "    $nfiles public files in scope (internal files excluded) — generic + PRIVATE belts + self-check"
else
  echo "    $nfiles public files in scope (internal files excluded) — generic belts only (no private config present)"
fi
echo "----"
run_all "$REPO_ROOT"
self_check
total=$(cat "$TOTAL_FILE")
echo "----"
if [ "${total:-0}" -eq 0 ]; then
  echo "==> research leak-scan: CLEAN — 0 findings."
  exit 0
fi
echo "==> research leak-scan: $total FINDING(S) — fail-closed. Resolve at source before any public push."
exit 1
