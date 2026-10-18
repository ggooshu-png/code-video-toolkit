#!/usr/bin/env bash
# 发布新版本：提交、打标签 vN、推送；版本超过 10 个时删除最早的 5 个版本标签。
# 用法: scripts/release.sh "本版说明"
set -euo pipefail
cd "$(dirname "$0")/.."
msg="${1:?需要版本说明}"
last=$(git tag -l 'v*' | sed 's/^v//' | sort -n | tail -1)
next=$(( ${last:-0} + 1 ))
printf '\n## v%s (%s)\n%s\n' "$next" "$(date +%F)" "$msg" >> CHANGELOG.md
git add -A
git commit -q -m "v$next: $msg" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
git tag -a "v$next" -m "$msg"
remote=$(git remote | head -1 || true)
[ -n "$remote" ] && git push -q -u "$remote" HEAD && git push -q "$remote" "v$next"
count=$(git tag -l 'v*' | wc -l)
if [ "$count" -gt 10 ]; then
  for t in $(git tag -l 'v*' | sed 's/^v//' | sort -n | head -5); do
    git tag -d "v$t" >/dev/null
    [ -n "$remote" ] && git push -q "$remote" ":refs/tags/v$t"
    echo "已删除旧版本 v$t"
  done
fi
echo "已发布 v$next"
