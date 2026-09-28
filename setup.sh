#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ "$repo_dir" != "$HOME/.agents" ]]; then
  printf 'Clone this repository to ~/.agents before running setup.sh\n' >&2
  exit 1
fi
if ! command -v skillshare >/dev/null 2>&1; then
  printf 'Install skillshare first: https://skillshare.runkids.cc/docs/\n' >&2
  exit 1
fi

shared_config="$repo_dir/config.yaml"
config_path="$HOME/.config/skillshare/config.yaml"
if [[ -n "${SKILLSHARE_CONFIG:-}" && "$SKILLSHARE_CONFIG" != "$shared_config" ]]; then
  printf 'SKILLSHARE_CONFIG points elsewhere; unset it before setup to use %s\n' "$shared_config" >&2
  exit 1
fi
if [[ -e "$config_path" || -L "$config_path" ]]; then
  if [[ ! "$config_path" -ef "$shared_config" ]]; then
    printf 'Existing skillshare config differs: %s\nBack it up or reconcile it before setup.\n' "$config_path" >&2
    exit 1
  fi
else
  mkdir -p -- "$(dirname -- "$config_path")"
  ln -s -- "$shared_config" "$config_path"
fi

skillshare install
skillshare sync
