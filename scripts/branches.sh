#!/usr/bin/env bash
# Funções para os branches `estado` (manifesto, pequeno) e `media` (vídeos públicos para o Buffer).
REMOTE="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}"
prep() {  # $1=branch  $2=pasta
  rm -rf "$2"
  git clone -q --depth=1 -b "$1" "$REMOTE" "$2" 2>/dev/null || mkdir -p "$2"
}
_git() { git config user.name github-actions; git config user.email actions@github.com; }
push_estado() {
  cd /tmp/estado && rm -rf .git && git init -q -b estado && _git
  git add -A && git commit -q -m "estado $(date +%F-%H%M)" && git push -q -f "$REMOTE" HEAD:estado
  cd "$GITHUB_WORKSPACE"
}
push_media() {
  cd /tmp/media && rm -rf .git && git init -q -b media && _git
  git add -A && git commit -q -m "media $(date +%F-%H%M)" && git push -q -f "$REMOTE" HEAD:media
  cd "$GITHUB_WORKSPACE"
}
