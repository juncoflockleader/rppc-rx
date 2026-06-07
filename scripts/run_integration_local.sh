#!/usr/bin/env bash
# Spin up a throwaway local Postgres (with pgvector) and run the test suite
# against it. Verifies the integration tests before/while CI is enabled.
# Not part of the app; safe to delete.
set -euo pipefail

# macOS: avoid "postmaster became multithreaded during startup" by pinning locale.
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

# Prefer a postgres major that pgvector was built for (brew bottle: 17/18).
PGBIN=""
for v in 17 18 16 15; do
  d="$(brew --prefix 2>/dev/null)/opt/postgresql@${v}/bin"
  if [ -x "${d}/postgres" ] && [ -f "$(${d}/pg_config --sharedir)/extension/vector.control" ]; then
    PGBIN="${d}"; break
  fi
done
[ -n "${PGBIN}" ] || { echo "no pgvector-capable postgres found"; exit 1; }
export PATH="${PGBIN}:${PATH}"
echo "using postgres: ${PGBIN}"

# Ensure the vector module is linked into pkglibdir (brew bottle ships it in the
# cellar but doesn't always symlink it).
PKGLIB="$(pg_config --pkglibdir)"
if [ ! -e "${PKGLIB}/vector.dylib" ]; then
  CELLAR_SO="$(find "$(brew --prefix)/Cellar/pgvector" -path "*$(basename "$(dirname "${PKGLIB}")")*/vector.dylib" 2>/dev/null | head -1)"
  [ -z "${CELLAR_SO}" ] && CELLAR_SO="$(find "$(brew --prefix)/Cellar/pgvector" -name vector.dylib 2>/dev/null | grep "$(basename "${PKGLIB}")" | head -1)"
  [ -n "${CELLAR_SO}" ] && ln -sf "${CELLAR_SO}" "${PKGLIB}/vector.dylib" || true
fi

ROOT="$(mktemp -d /tmp/rppc-pg.XXXXXX)"
DATA="${ROOT}/data"; SOCK="${ROOT}/sock"; mkdir -p "${SOCK}"
PORT=54332

cleanup() { pg_ctl -D "${DATA}" -m immediate stop >/dev/null 2>&1 || true; rm -rf "${ROOT}"; }
trap cleanup EXIT

initdb -D "${DATA}" -U postgres --auth=trust >/dev/null
pg_ctl -D "${DATA}" -l "${ROOT}/log" \
  -o "-p ${PORT} -k ${SOCK} -c listen_addresses=''" -w start
createdb -h "${SOCK}" -p "${PORT}" -U postgres podcast_synthesis

export TEST_DATABASE_URL="postgresql://postgres@/podcast_synthesis?host=${SOCK}&port=${PORT}"
echo "TEST_DATABASE_URL set."

cd "$(dirname "$0")/../backend"
. .venv/bin/activate
python -m pytest tests "$@"
