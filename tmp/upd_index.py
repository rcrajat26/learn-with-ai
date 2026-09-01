#!/usr/bin/env python3
"""Flips file-plan rows to `written` with real line counts, from what is on disk."""
import os, re, subprocess

TOPIC = "/Users/rajat.chikkodikar/Desktop/My-files/rough/src/notes/detailed/04-modern-java"
IDX = f"{TOPIC}/00-index.md"

src = open(IDX).read().split('\n')
out = []
done = 0
for l in src:
    m = re.match(r'^\| (\d+) \| `([^`]+\.md)` \| (.*)\| (planned|written|blocked) \| ?(\d*) \|$', l)
    if m:
        n, f, mid, status, _ = m.groups()
        path = f"{TOPIC}/{f}"
        if os.path.exists(path):
            cnt = sum(1 for _ in open(path, errors='replace'))
            l = f"| {n} | `{f}` | {mid}| written | {cnt} |"
            done += 1
        else:
            l = f"| {n} | `{f}` | {mid}| planned |  |"
    out.append(l)
open(IDX, 'w').write('\n'.join(out))
total = 0
for root, _, fs in os.walk(TOPIC):
    for f in fs:
        if f.endswith('.md'):
            total += sum(1 for _ in open(os.path.join(root, f), errors='replace'))
print(f"rows written: {done}/69 · total md lines incl. index: {total}")
