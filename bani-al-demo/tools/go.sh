cd ~/.claude/skills/bani-al-demo/scripts
for s in "$@"; do python /c/dev/bani-al-demo/tools/perfume_fill.py $s && PYTHONIOENCODING=utf-8 python build.py $s 2>&1 | tail -1 && PYTHONIOENCODING=utf-8 python check.py $s 2>&1 | grep -E "^(PASS|FAIL)|FAIL "; done
