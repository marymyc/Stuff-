#!/usr/bin/env bash
# Pushes ./reports (+ logs) to the `ci-report` branch so results are readable without opening Actions.
# Usage: bash scripts/publish_report.sh <job-name>     (env: JOB_STATUS, GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_SHA)
set -u
name="${1:?job name}"
status="${JOB_STATUS:-unknown}"
tmp="$(mktemp -d)"
rm -rf reports/blender_preflight/frames reports/blender_preflight/sprites 2>/dev/null || true
[ -d reports ] && cp -r reports/. "$tmp/"
for f in pytest.log smoke.log e2e.log; do [ -f "$f" ] && cp "$f" "$tmp/"; done
for d in work/smoke work/blender_smoke work/voice_e2e; do
  [ -f "$d/report.json" ] && cp "$d/report.json" "$tmp/$(basename "$d")_report.json"
done
pip freeze > "$tmp/pip-freeze.txt" 2>/dev/null || true
printf '{"job":"%s","status":"%s","sha":"%s","run":"%s","time":"%s"}\n' "$name" "$status" "${GITHUB_SHA:-}" "${GITHUB_RUN_ID:-}" "$(date -u +%FT%TZ)" > "$tmp/meta.json"
url="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
for attempt in 1 2 3 4; do
  rm -rf /tmp/rb
  if ! git clone --quiet --depth 1 --branch ci-report "$url" /tmp/rb 2>/dev/null; then
    rm -rf /tmp/rb && mkdir /tmp/rb && (cd /tmp/rb && git init -q && git checkout -q -b ci-report && git remote add origin "$url")
  fi
  rm -rf "/tmp/rb/$name" && mkdir -p "/tmp/rb/$name" && cp -r "$tmp/." "/tmp/rb/$name/"
  if (cd /tmp/rb && git config user.name "github-actions[bot]" && git config user.email "41898282+github-actions[bot]@users.noreply.github.com" \
      && git add -A && git commit -q -m "report: $name $status ${GITHUB_SHA:0:7}" && git push -q origin ci-report); then
    echo "report published for $name"; exit 0
  fi
  sleep $((attempt * 3))
done
echo "could not publish report"; exit 0
