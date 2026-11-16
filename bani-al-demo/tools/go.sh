# fill + build + check several perfume demos: bash go.sh <slug> [<slug> ...]
T="$(cd "$(dirname "$0")" && pwd)"
cd ~/.claude/skills/bani-al-demo/scripts
for s in "$@"; do python "$T/perfume_fill.py" $s && PYTHONIOENCODING=utf-8 python build.py $s 2>&1 | tail -1 && PYTHONIOENCODING=utf-8 python check.py $s 2>&1 | grep -E "^(PASS|FAIL)|FAIL "; done
