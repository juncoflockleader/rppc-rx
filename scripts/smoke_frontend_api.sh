#!/usr/bin/env bash
# Bring up a live backend (local pgvector Postgres + uvicorn) and curl the exact
# endpoints the frontend client calls, to validate the contract. Not part of CI.
set -euo pipefail
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

PGBIN=""
for v in 17 18 16 15; do
  d="$(brew --prefix 2>/dev/null)/opt/postgresql@${v}/bin"
  if [ -x "${d}/postgres" ] && [ -f "$(${d}/pg_config --sharedir)/extension/vector.control" ]; then
    PGBIN="${d}"; break; fi
done
[ -n "${PGBIN}" ] || { echo "no pgvector postgres"; exit 1; }
export PATH="${PGBIN}:${PATH}"
PKGLIB="$(pg_config --pkglibdir)"
[ -e "${PKGLIB}/vector.dylib" ] || ln -sf \
  "$(find "$(brew --prefix)/Cellar/pgvector" -name vector.dylib | grep "$(basename "${PKGLIB}")" | head -1)" \
  "${PKGLIB}/vector.dylib" 2>/dev/null || true

ROOT="$(mktemp -d /tmp/rppc-smoke.XXXXXX)"; DATA="${ROOT}/data"; SOCK="${ROOT}/sock"; mkdir -p "${SOCK}"
PORT=54400; UVPORT=8077; UVPID=""
cleanup() {
  [ -n "${UVPID}" ] && kill "${UVPID}" 2>/dev/null || true
  pg_ctl -D "${DATA}" -m immediate stop >/dev/null 2>&1 || true
  rm -rf "${ROOT}"
}
trap cleanup EXIT

initdb -D "${DATA}" -U postgres --auth=trust >/dev/null
pg_ctl -D "${DATA}" -o "-p ${PORT} -k ${SOCK} -c listen_addresses='127.0.0.1'" -w start >/dev/null
createdb -h "${SOCK}" -p "${PORT}" -U postgres podcast_synthesis

cd "$(dirname "$0")/../backend"
. .venv/bin/activate
python -c "import uvicorn" 2>/dev/null || pip install -q "uvicorn[standard]"
export DATABASE_URL="postgresql://postgres@127.0.0.1:${PORT}/podcast_synthesis"
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f migrations/000_apply_all.sql >/dev/null
python -m app.personas_import >/dev/null
echo "personas seeded."

uvicorn app.main:app --port "${UVPORT}" --log-level warning &
UVPID=$!
for _ in $(seq 1 40); do curl -fsS "http://127.0.0.1:${UVPORT}/health" >/dev/null 2>&1 && break; sleep 0.25; done

H=(-H "Authorization: Bearer dev-token" -H "Content-Type: application/json")
api() { curl -fsS "${H[@]}" "$@"; }
B="http://127.0.0.1:${UVPORT}"

echo "== health =="; api "${B}/health"
PID=$(api -X POST "${B}/api/projects" -d '{"title":"Smoke"}' | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo; echo "project: ${PID}"
SID=$(api -X POST "${B}/api/projects/${PID}/sources/text" \
  -d '{"title":"Essay","text":"Modern desire is intensified by social comparison. It grows with measurement."}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "source: ${SID}"
JID=$(api -X POST "${B}/api/projects/${PID}/sources/${SID}/process" | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
echo "job: ${JID}"
for _ in $(seq 1 60); do
  ST=$(api "${B}/api/jobs/${JID}" | python -c "import sys,json;print(json.load(sys.stdin)['status'])")
  [ "${ST}" = "completed" ] || [ "${ST}" = "failed" ] && break; sleep 0.5
done
echo "job status: ${ST}"
echo "== summary =="; api "${B}/api/sources/${SID}/summary"
echo
echo "== personas =="; api "${B}/api/personas" | python -c "import sys,json;print([p['persona_id'] for p in json.load(sys.stdin)])"

echo "== episode create =="
EID=$(api -X POST "${B}/api/projects/${PID}/episodes" -d '{
  "title":"Desire","goal":"Understand desire","target_duration_seconds":600,
  "personas":[
    {"persona_id":"modern_host","version":"v1.0","role":"host","speaker_label":"HOST"},
    {"persona_id":"laozi","version":"v1.0","role":"guest","speaker_label":"LAOZI"},
    {"persona_id":"buddha","version":"v1.0","role":"guest","speaker_label":"BUDDHA"}]}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "episode: ${EID}"
echo "list episodes:"; api "${B}/api/projects/${PID}/episodes" | python -c "import sys,json;print(len(json.load(sys.stdin)),'episode(s)')"
PJID=$(api -X POST "${B}/api/episodes/${EID}/discussion-plan" | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
for _ in $(seq 1 120); do
  PST=$(api "${B}/api/jobs/${PJID}" | python -c "import sys,json;print(json.load(sys.stdin)['status'])")
  [ "${PST}" = "completed" ] || [ "${PST}" = "failed" ] && break; sleep 0.5
done
echo "plan job: ${PST}"
echo "role context speakers:"; api "${B}/api/episodes/${EID}/role-context" | python -c "import sys,json;print([c['speaker_label'] for c in json.load(sys.stdin)['cards']])"
echo "plan beats:"; api "${B}/api/episodes/${EID}/discussion-plan" | python -c "import sys,json;d=json.load(sys.stdin);print('v%d,'%d['version'], len(d['plan']['beats']),'beats')"

echo "== script generation =="
SJID=$(api -X POST "${B}/api/episodes/${EID}/scripts" | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
for _ in $(seq 1 120); do
  SST=$(api "${B}/api/jobs/${SJID}" | python -c "import sys,json;print(json.load(sys.stdin)['status'])")
  [ "${SST}" = "completed" ] || [ "${SST}" = "failed" ] && break; sleep 0.5
done
echo "script job: ${SST}"
SCRIPT=$(api "${B}/api/episodes/${EID}/scripts/latest")
VID=$(echo "${SCRIPT}" | python -c "import sys,json;print(json.load(sys.stdin)['script_version_id'])")
SEG0=$(echo "${SCRIPT}" | python -c "import sys,json;print(json.load(sys.stdin)['segments'][0]['id'])")
echo "script:"; echo "${SCRIPT}" | python -c "import sys,json;d=json.load(sys.stdin);print(len(d['segments']),'segments, safety=',d['safety_status'])"

echo "== edit + rewrite =="
api -X PATCH "${B}/api/script-segments/${SEG0}" -d '{"text":"An edited opening line for the host."}' | python -c "import sys,json;print('edited ->',json.load(sys.stdin)['status'])"
api -X POST "${B}/api/script-segments/${SEG0}/rewrite" -d '{"instruction":"make it warmer"}' | python -c "import sys,json;print('rewrite ->',json.load(sys.stdin)['text'][:40])"

echo "== QA =="
QJID=$(api -X POST "${B}/api/scripts/${VID}/qa" | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
for _ in $(seq 1 120); do
  QST=$(api "${B}/api/jobs/${QJID}" | python -c "import sys,json;print(json.load(sys.stdin)['status'])")
  [ "${QST}" = "completed" ] || [ "${QST}" = "failed" ] && break; sleep 0.5
done
echo "qa job: ${QST}"
api "${B}/api/scripts/${VID}/qa" | python -c "import sys,json;d=json.load(sys.stdin);print('safety=',d['safety_status'],'| reports:',sorted(r['report_type'] for r in d['reports']))"
echo "repair:"; api -X POST "${B}/api/scripts/${VID}/repair" | python -c "import sys,json;print(json.load(sys.stdin)['count'],'segment(s) repaired')"

echo "== audio render =="
AJID=$(api -X POST "${B}/api/episodes/${EID}/audio" | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
for _ in $(seq 1 120); do
  AST=$(api "${B}/api/jobs/${AJID}" | python -c "import sys,json;print(json.load(sys.stdin)['status'])")
  [ "${AST}" = "completed" ] || [ "${AST}" = "failed" ] && break; sleep 0.5
done
echo "audio job: ${AST}"
DURL=$(api "${B}/api/episodes/${EID}/audio/latest" | python -c "import sys,json;d=json.load(sys.stdin);print(d['download_url'])")
TMPA=$(mktemp); api "${B}${DURL}" -o "${TMPA}"; HDR=$(head -c 4 "${TMPA}" | tr -d '\0'); rm -f "${TMPA}"
echo "audio download starts with: ${HDR}  (expect RIFF)"

echo "== export =="
XJID=$(api -X POST "${B}/api/episodes/${EID}/export" | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
for _ in $(seq 1 120); do
  XST=$(api "${B}/api/jobs/${XJID}" | python -c "import sys,json;print(json.load(sys.stdin)['status'])")
  [ "${XST}" = "completed" ] || [ "${XST}" = "failed" ] && break; sleep 0.5
done
echo "export job: ${XST}"
XURL=$(api "${B}/api/episodes/${EID}/export/latest" | python -c "import sys,json;d=json.load(sys.stdin);print(' '.join(d['manifest']['files']));import sys" )
echo "package files: ${XURL}"
DL=$(api "${B}/api/episodes/${EID}/export/latest" | python -c "import sys,json;print(json.load(sys.stdin)['download_url'])")
TMPZ=$(mktemp); api "${B}${DL}" -o "${TMPZ}"; ZHDR=$(head -c 2 "${TMPZ}"); rm -f "${TMPZ}"
echo "zip download starts with: ${ZHDR}  (expect PK)"

echo "== cost =="; api "${B}/api/episodes/${EID}/cost" | python -c "import sys,json;d=json.load(sys.stdin);print('llm_calls=%d tts_calls=%d est=\$%s'%(d['llm_calls'],d['tts_calls'],d['estimated_llm_cost_usd']))"
echo "== feedback =="; api -X POST "${B}/api/feedback" -d '{"target_type":"episode","target_id":"'"${EID}"'","episode_id":"'"${EID}"'","feedback_type":"thumbs","rating":1}' | python -c "import sys,json;print(json.load(sys.stdin)['status'])"
echo "== notices =="; api "${B}/api/meta/notices" | python -c "import sys,json;print('disclaimer present:', bool(json.load(sys.stdin)['disclaimer_en']))"
echo "SMOKE_OK"
