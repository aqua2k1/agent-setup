#!/usr/bin/env bash

LOCK="${1:-$HOME/.agents/.skill-lock.json}"
WANTED="$(mktemp)"
CURRENT="$(mktemp)"
trap 'rm -f "$WANTED" "$CURRENT"' EXIT

jq -r '.skills | keys[]' "$LOCK" > "$WANTED"
npx skills ls -g --agent universal --json | jq -r '.[].name' > "$CURRENT"

# 删除多余的
while IFS= read -r name; do
  if ! grep -qxF "$name" "$WANTED"; then
    echo "==> remove $name"
    npx skills remove -g "$name" --agent universal -y </dev/null
  fi
done < "$CURRENT"

# 安装缺少的
while IFS=$'\t' read -r source name; do
  if ! grep -qxF "$name" "$CURRENT"; then
    echo "==> add $source --skill $name"
    npx skills add "$source" -g --skill "$name" --agent universal -y </dev/null
  fi
done < <(
  jq -r '.skills | to_entries[] | [.value.source, .key] | @tsv' "$LOCK"
)

npx skills ls -g --agent universal
