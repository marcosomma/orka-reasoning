#!/usr/bin/env bash
#
# OrKa self-assessment runner.
#
# Runs every assessment workflow in this folder and prints a global report.
# Auto-discovers *.yml so newly added assessments are picked up with no edits.
#
# Usage:
#   ./examples/self_assessment/check.sh                 # run every *.yml here
#   ./examples/self_assessment/check.sh foo.yml bar.yml # run only these
#
# Env:
#   ORKA_TIMEOUT_SECONDS   passed through to the engine (default 600 if unset)
#   ORKA_INPUT             input string given to each workflow (default "test")
#
# Exit code: 0 only if every workflow completed AND no explicit FAIL verdict was
# emitted; non-zero otherwise. Requires Redis (orka-start) + an LLM at model_url.

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Prefer the repo venv if present, else whatever python is on PATH.
if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PY="${REPO_ROOT}/.venv/bin/python"
else
  PY="$(command -v python3 || command -v python)"
fi

export ORKA_TIMEOUT_SECONDS="${ORKA_TIMEOUT_SECONDS:-600}"
INPUT="${ORKA_INPUT:-test}"

# Collect the workflows to run: explicit args, or every *.yml in this folder.
declare -a FILES=()
if [[ "$#" -gt 0 ]]; then
  for arg in "$@"; do FILES+=("$arg"); done
else
  shopt -s nullglob
  for f in "${SCRIPT_DIR}"/*.yml; do FILES+=("$f"); done
  shopt -u nullglob
fi

if [[ "${#FILES[@]}" -eq 0 ]]; then
  echo "No assessment workflows (*.yml) found in ${SCRIPT_DIR}" >&2
  exit 2
fi

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/orka-selfassess.XXXXXX")"
trap 'rm -rf "${LOG_DIR}"' EXIT

declare -a NAMES=() VERDICTS=() SECS=()
total=0; passed=0; failed=0; ran=0; errored=0

echo "Running ${#FILES[@]} self-assessment workflow(s) (timeout=${ORKA_TIMEOUT_SECONDS}s)..."
echo

for file in "${FILES[@]}"; do
  name="$(basename "${file}")"
  log="${LOG_DIR}/${name}.log"
  total=$((total + 1))

  start=$(date +%s)
  "${PY}" -m orka.orka_cli run "${file}" "${INPUT}" >"${log}" 2>&1
  code=$?
  end=$(date +%s)
  secs=$((end - start))

  # Verdict: exit code is the reliable signal; the explicit PASS/FAIL verdict
  # (when an assessment emits one) is parsed best-effort from the LAST "overall"
  # line in the output, which is the final report agent's response.
  if [[ "${code}" -ne 0 ]]; then
    verdict="ERROR (exit ${code})"
    errored=$((errored + 1))
  else
    # Drop the prompt template line (`"overall": "PASS" or "FAIL"`) so only a real
    # emitted verdict counts; take the last surviving match as the final report.
    last_overall="$(grep -E '"overall"' "${log}" \
      | grep -vF '"PASS" or "FAIL"' \
      | grep -oE '"overall"[[:space:]]*:[[:space:]]*"?(PASS|FAIL)"?' \
      | tail -n1 || true)"
    if [[ "${last_overall}" == *FAIL* ]]; then
      verdict="FAIL"
      failed=$((failed + 1))
    elif [[ "${last_overall}" == *PASS* ]]; then
      verdict="PASS"
      passed=$((passed + 1))
    else
      verdict="RAN (no verdict)"
      ran=$((ran + 1))
    fi
  fi

  NAMES+=("${name}"); VERDICTS+=("${verdict}"); SECS+=("${secs}")
  printf '  %-48s %-18s %4ss\n' "${name}" "${verdict}" "${secs}"
done

echo
echo "================= SELF-ASSESSMENT REPORT ================="
printf '%-48s %-18s %6s\n' "WORKFLOW" "VERDICT" "TIME"
printf '%-48s %-18s %6s\n' "--------" "-------" "----"
for i in "${!NAMES[@]}"; do
  printf '%-48s %-18s %5ss\n' "${NAMES[$i]}" "${VERDICTS[$i]}" "${SECS[$i]}"
done
echo "---------------------------------------------------------"
echo "total=${total}  PASS=${passed}  FAIL=${failed}  RAN=${ran}  ERROR=${errored}"
echo "========================================================="

# Show captured output for anything that did not cleanly pass/run, to aid debugging.
if [[ $((failed + errored)) -gt 0 ]]; then
  echo
  echo "Failures/errors detail (last 25 lines each):"
  for i in "${!NAMES[@]}"; do
    case "${VERDICTS[$i]}" in
      FAIL*|ERROR*)
        echo "----- ${NAMES[$i]} (${VERDICTS[$i]}) -----"
        tail -n 25 "${LOG_DIR}/${NAMES[$i]}.log"
        echo
        ;;
    esac
  done
fi

# Non-zero if anything errored or explicitly failed.
[[ $((failed + errored)) -eq 0 ]]
