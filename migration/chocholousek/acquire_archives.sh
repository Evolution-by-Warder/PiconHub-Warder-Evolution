#!/bin/sh
# PiconHub-Warder-Evolution — one-time Chocholousek archive acquisition
#
# Downloads ONLY rows present in source_manifest.tsv. No crawling, scraping,
# concurrency, CAPTCHA handling, anti-bot bypass, or URL discovery is performed.
# Each successful file is 7z-tested, SHA256-recorded and checkpointed so a
# restarted run skips already verified files.

set -eu

MANIFEST=${MANIFEST:-source_manifest.tsv}
OUT=${OUT:-./chocholousek-acquisition}
LIMIT=${LIMIT:-50}
START=${START:-1}
SLEEP=${SLEEP:-2}
USER_AGENT=${USER_AGENT:-PiconHub-Warder-Evolution-migration/1.0}

STATE="$OUT/state.tsv"
FAILS="$OUT/failures.tsv"
LOG="$OUT/acquisition.log"

usage() {
    cat <<EOF
Usage: MANIFEST=/path/source_manifest.tsv [OUT=/path/output] [START=1] [LIMIT=50] [SLEEP=2] $0

Environment:
  MANIFEST  exact migration TSV (default: source_manifest.tsv)
  OUT       destination/checkpoint directory (default: ./chocholousek-acquisition)
  START     1-based manifest data row to start from (default: 1)
  LIMIT     maximum number of manifest rows attempted this run; 0 = no limit
  SLEEP     seconds between network attempts (default: 2)

Required commands: curl, 7z (or 7za), sha256sum, awk, wc, date
EOF
}

[ "${1:-}" = "--help" ] && { usage; exit 0; }
[ -f "$MANIFEST" ] || { echo "ERROR: manifest not found: $MANIFEST" >&2; exit 2; }
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required" >&2; exit 2; }
command -v sha256sum >/dev/null 2>&1 || { echo "ERROR: sha256sum is required" >&2; exit 2; }
if command -v 7z >/dev/null 2>&1; then
    SEVENZ=7z
elif command -v 7za >/dev/null 2>&1; then
    SEVENZ=7za
else
    echo "ERROR: 7z or 7za is required" >&2
    exit 2
fi

mkdir -p "$OUT/raw" "$OUT/tmp"
[ -f "$STATE" ] || printf 'id\tfilename\tresolution\tbackground\ttarget\tsha256\tsize_bytes\tacquired_utc\tsource_url\tfinal_url\n' > "$STATE"
[ -f "$FAILS" ] || printf 'id\tfilename\tutc\treason\tsource_url\n' > "$FAILS"
: >> "$LOG"

# Check exact expected manifest header before touching the network.
HEADER=$(sed -n '1p' "$MANIFEST")
EXPECTED='id\tfilename\tresolution\tbackground\ttarget\tsource_url\tarchive_type\tprovenance'
[ "$HEADER" = "$(printf '%b' "$EXPECTED")" ] || {
    echo "ERROR: unexpected manifest header" >&2
    echo "Got: $HEADER" >&2
    exit 2
}

already_done() {
    _id=$1
    _filename=$2
    awk -F '\t' -v id="$_id" -v fn="$_filename" 'NR>1 && $1==id && $2==fn {found=1} END {exit !found}' "$STATE"
}

record_failure() {
    _id=$1; _filename=$2; _reason=$3; _url=$4
    _utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    printf '%s\t%s\t%s\t%s\t%s\n' "$_id" "$_filename" "$_utc" "$_reason" "$_url" >> "$FAILS"
    printf '[%s] FAIL id=%s file=%s reason=%s\n' "$_utc" "$_id" "$_filename" "$_reason" | tee -a "$LOG" >&2
}

TOTAL=$(awk 'END{print NR-1}' "$MANIFEST")
ATTEMPTED=0
OK=0
SKIPPED=0
FAILED=0
ROW=0

# POSIX read with tab-separated fields; filenames in this source do not contain tabs.
TAB=$(printf '\t')
while IFS="$TAB" read -r id filename resolution background target source_url archive_type provenance; do
    [ "$id" = "id" ] && continue
    ROW=$((ROW + 1))
    [ "$ROW" -lt "$START" ] && continue
    if [ "$LIMIT" -gt 0 ] && [ "$ATTEMPTED" -ge "$LIMIT" ]; then
        break
    fi

    if already_done "$id" "$filename"; then
        SKIPPED=$((SKIPPED + 1))
        printf '[checkpoint] skip verified %s/%s id=%s %s\n' "$ROW" "$TOTAL" "$id" "$filename" | tee -a "$LOG"
        continue
    fi

    ATTEMPTED=$((ATTEMPTED + 1))

    case "$archive_type" in
        preview) destdir="$OUT/raw/preview" ;;
        core)    destdir="$OUT/raw/$resolution/$background" ;;
        *)
            FAILED=$((FAILED + 1))
            record_failure "$id" "$filename" "unknown_archive_type:$archive_type" "$source_url"
            continue
            ;;
    esac
    mkdir -p "$destdir"
    final="$destdir/$filename"
    part="$OUT/tmp/$id.part"
    headers="$OUT/tmp/$id.headers"

    # If a complete file exists but is not checkpointed, validate it locally first.
    if [ -f "$final" ]; then
        if "$SEVENZ" t -y "$final" >/dev/null 2>&1; then
            sha=$(sha256sum "$final" | awk '{print $1}')
            size=$(wc -c < "$final" | tr -d ' ')
            utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
            printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
                "$id" "$filename" "$resolution" "$background" "$target" "$sha" "$size" "$utc" "$source_url" "local-existing" >> "$STATE"
            OK=$((OK + 1))
            printf '[%s] OK existing %s/%s id=%s size=%s sha256=%s %s\n' "$utc" "$ROW" "$TOTAL" "$id" "$size" "$sha" "$filename" | tee -a "$LOG"
            continue
        fi
        mv "$final" "$final.invalid.$(date -u '+%Y%m%dT%H%M%SZ')"
    fi

    printf '[download] %s/%s id=%s %s\n' "$ROW" "$TOTAL" "$id" "$filename" | tee -a "$LOG"
    rm -f "$headers"

    # Normal HTTP download only. -C - resumes a partial transfer when the server supports it.
    # --retry is limited to transient transport/5xx failures; no protection is bypassed.
    if ! curl -fL -C - \
        --connect-timeout 20 \
        --max-time 1800 \
        --retry 3 \
        --retry-delay 5 \
        --user-agent "$USER_AGENT" \
        -D "$headers" \
        -o "$part" \
        "$source_url"; then
        FAILED=$((FAILED + 1))
        record_failure "$id" "$filename" "download_failed" "$source_url"
        sleep "$SLEEP"
        continue
    fi

    if ! "$SEVENZ" t -y "$part" >/dev/null 2>&1; then
        FAILED=$((FAILED + 1))
        bad="$OUT/tmp/$id.invalid.$(date -u '+%Y%m%dT%H%M%SZ')"
        mv "$part" "$bad"
        record_failure "$id" "$filename" "7z_test_failed:$bad" "$source_url"
        sleep "$SLEEP"
        continue
    fi

    sha=$(sha256sum "$part" | awk '{print $1}')
    size=$(wc -c < "$part" | tr -d ' ')
    utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    final_url=$(awk 'BEGIN{IGNORECASE=1} /^location:/ {sub(/^[^:]*:[[:space:]]*/,""); sub(/\r$/,""); loc=$0} END{print loc}' "$headers")
    [ -n "$final_url" ] || final_url="$source_url"

    mv "$part" "$final"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$id" "$filename" "$resolution" "$background" "$target" "$sha" "$size" "$utc" "$source_url" "$final_url" >> "$STATE"
    OK=$((OK + 1))
    printf '[%s] OK %s/%s id=%s size=%s sha256=%s %s\n' "$utc" "$ROW" "$TOTAL" "$id" "$size" "$sha" "$filename" | tee -a "$LOG"
    sleep "$SLEEP"
done < "$MANIFEST"

printf '\nCheckpoint: total=%s start=%s attempted=%s ok=%s skipped=%s failed=%s\n' \
    "$TOTAL" "$START" "$ATTEMPTED" "$OK" "$SKIPPED" "$FAILED" | tee -a "$LOG"
printf 'State: %s\nFailures: %s\nRaw: %s/raw\n' "$STATE" "$FAILS" "$OUT"

[ "$FAILED" -eq 0 ]
