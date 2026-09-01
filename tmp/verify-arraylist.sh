#!/bin/bash
# Adapted from the spec's verify.sh for macOS bash 3.2 with no GNU coreutils:
#   - mapfile  -> while-read into positional handling
#   - grep -P  -> python3 for the emoji scan
# Every other check is semantically identical to the spec.
set -uo pipefail
ROOT="/Users/rajat.chikkodikar/Desktop/My-files/rough/src/notes/tailored/topic/$1"
fail=0
bad(){ printf 'FAIL  %s\n' "$1"; fail=1; }

[ -f "$ROOT/00-map.md" ] || bad "no 00-map.md"
grep -q 'planned' "$ROOT/00-map.md" && bad "rows still planned in map"
grep -q '## Question inventory' "$ROOT/00-map.md" || bad "map has no question inventory"
grep -q '## Source ledger'      "$ROOT/00-map.md" || bad "map has no source ledger"
grep -rq '## Atomic concept checklist' "$ROOT" || bad "no atomic concept checklist"

find "$ROOT" -maxdepth 2 -name '*.md' | sort | while read -r f; do
  case "$f" in *00-map.md) continue;; esac
  n=$(wc -l < "$f" | tr -d ' ')
  [ "$n" -gt 600 ] && bad "$f is $n lines, unsplit"
  for s in '## Pitfalls' '## Cheat sheet' '## Self-test' '**Questions answered:**' \
           '**Target version:**' '**Diagrams included:**' 'Assumes:'; do
    grep -qF "$s" "$f" || bad "$f missing $s"
  done
  d=$(grep -c '<details>' "$f" | tr -d ' ')
  { [ "$d" -ge 5 ] && [ "$d" -le 10 ]; } || bad "$f has $d self-test answers, want 5-10"
  grep -q 'src/notes/detailed' "$f" && bad "$f leaks a provenance path"
  grep -qiE 'sourced from|adapted from' "$f" && bad "$f has a provenance line"
done

grep -rl '<svg' "$ROOT" --include='*.md' 2>/dev/null | while read -r f; do bad "inline svg in $f"; done

python3 - "$ROOT" <<'PY'
import sys, pathlib, re
rx = re.compile('[\U0001F300-\U0001FAFF☀-➿]')
for p in pathlib.Path(sys.argv[1]).rglob('*.md'):
    hits = rx.findall(p.read_text(encoding='utf-8', errors='replace'))
    if hits:
        print('FAIL  emoji in %s: %r' % (p, sorted(set(hits))))
PY

grep -rn 'implementation omitted\|TODO\|and so on' "$ROOT" --include='*.md' 2>/dev/null \
  | while read -r l; do bad "elision: $l"; done
grep -rnwE 'Foo|Bar|Baz|MyClass|thread1|thread2|doSomething|Dog|Cat|Animal|Shape|Circle|Square' \
  "$ROOT" --include='*.md' 2>/dev/null | while read -r l; do bad "throwaway example: $l"; done

# diagram coverage, both directions
grep -o 'D-[0-9][0-9]' "$ROOT/00-map.md" | sort -u | while read -r id; do
  ls "$ROOT/diagrams/$id"-*.svg >/dev/null 2>&1 || bad "$id in manifest, no svg"
  grep -rq "$id" "$ROOT" --include='*.md' || bad "$id never embedded"
done
find "$ROOT/diagrams" -name '*.svg' 2>/dev/null | while read -r s; do
  b=$(basename "$s")
  grep -rq "$b" "$ROOT" --include='*.md' || bad "$b orphaned"
  for a in viewBox 'role="img"' aria-label; do
    grep -q "$a" "$s" || bad "$b has no $a"
  done
  sed -n '1,/>/p' "$s" | grep -qE '[[:space:]](width|height)=' \
    && bad "$b has a fixed width/height on the svg element"
  grep -qE '<rect x="0" y="0"[^>]*fill="#ffffff"' "$s" || bad "$b has no backdrop rect"
  grep -qE '[[:space:]]d="[^"]*[CcQqSsTtAa]' "$s" && bad "$b has a curved or arc edge"
done

# every embed must resolve RELATIVE TO THE FILE IT SITS IN
find "$ROOT" -name '*.md' | while read -r f; do
  d=$(dirname "$f")
  grep -o '](\([^)]*\)\.svg)' "$f" | sed 's|^](||;s|)$||' | sort -u | while read -r p; do
    case "$p" in /*|http*) continue;; esac
    [ -f "$d/$p" ] || bad "broken diagram path in $f: $p"
  done
  grep -nE '!\[[^]]*\]\($' "$f" | while read -r l; do bad "multi-line image embed in $f: $l"; done
done

# extra: stray PNG scratch left by illustrators
find "$ROOT" -name '*.png' | while read -r p; do bad "scratch png left behind: $p"; done

echo "=== verify complete (read the FAIL lines; pipeline subshells mask \$?) ==="
