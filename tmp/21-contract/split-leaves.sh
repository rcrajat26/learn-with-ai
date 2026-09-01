#!/bin/bash
# split-leaves.sh <out-name> <first-leaf-id> <last-leaf-id>
# Extracts the verbatim leaf blocks for one sealed row out of the topic-21 prompt.
# A leaf block is a line starting with the leaf id at column 1, plus its indented
# continuation lines. Section headers (### §x.y) inside the range are kept.
P=/Users/rajat.chikkodikar/Desktop/My-files/rough/src/metadata/prompts/21-ai-for-coding-prompt.md
T=/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/21-contract/leaves
mkdir -p "$T"
OUT="$T/$1.md"
FIRST="$2"
LAST="$3"
awk -v first="$FIRST" -v last="$LAST" '
function idnum(s) {
  n = split(s, a, ".")
  return a[1] * 1000000 + a[2] * 1000 + a[3]
}
BEGIN { lo = idnum(first); hi = idnum(last); inrange = 0 }
/^### §/ { hdr = $0; next }
/^[0-9]+\.[0-9]+\.[0-9]+ / {
  id = $1
  v = idnum(id)
  if (v >= lo && v <= hi) {
    if (!inrange && hdr != "") { print hdr; print ""; }
    inrange = 1
    print
    next
  } else { inrange = 0; next }
}
{ if (inrange && (/^[[:space:]]/ || $0 == "")) print }
' "$P" > "$OUT"
printf '%s  %s lines  (%s..%s)\n' "$1" "$(wc -l < "$OUT" | tr -d ' ')" "$FIRST" "$LAST"
