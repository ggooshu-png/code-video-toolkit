#!/usr/bin/env bash
# 发布新版本：把当前 skills/、notes/、engine/、scripts/ 快照到 versions/vN/，提交并推送 main。
# 版本快照超过 10 个时删除最早的 5 个（历史仍在 git 提交里可查）。
# 说明：当前环境不允许推送 git 标签，所以版本以 versions/ 目录 + 提交信息 "vN:" 的形式保存。
# 用法: scripts/release.sh "本版说明"
set -euo pipefail
cd "$(dirname "$0")/.."
msg="${1:?需要版本说明}"
mkdir -p versions
last=$(ls versions | sed -n 's/^v\([0-9]*\)$/\1/p' | sort -n | tail -1)
next=$(( ${last:-0} + 1 ))
printf '\n## v%s (%s)\n%s\n' "$next" "$(date +%F)" "$msg" >> CHANGELOG.md
mkdir -p "versions/v$next"
cp -r skills notes engine scripts CHANGELOG.md "versions/v$next/"
count=$(ls versions | grep -c '^v[0-9]*$')
if [ "$count" -gt 10 ]; then
  for t in $(ls versions | sed -n 's/^v\([0-9]*\)$/\1/p' | sort -n | head -5); do
    rm -rf "versions/v$t"; echo "已删除旧版本 v$t"
  done
fi
git add -A
git commit -q -m "v$next: $msg" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
if git remote | grep -q origin; then git push -q -u origin main; fi
echo "已发布 v$next"
