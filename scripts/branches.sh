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
  git add -A && git commit -q -m "media $(date +%F-%H%M)" && { for t in 1 2 3 4; do git push -f "$REMOTE" HEAD:media 2>&1 | tail -4 | sed "s/^/::warning::push media: /"; [ "${PIPESTATUS[0]}" -eq 0 ] && break; [ $t -eq 4 ] && { cd "$GITHUB_WORKSPACE"; return 1; }; sleep $((t*20)); done; }
  cd "$GITHUB_WORKSPACE"
}
push_analises() {  # branch `analises`: so o cerebro escreve; historico preservado (push normal com retry, sem force)
  cd /tmp/analises
  [ -d .git ] || { git init -q -b analises; git remote add origin "$REMOTE"; }
  _git; git add -A; git commit -q -m "analises $(date +%F-%H%M)" || { cd "$GITHUB_WORKSPACE"; return 0; }
  for i in 1 2 3; do
    git push -q origin HEAD:analises 2>/dev/null && break
    git fetch -q origin analises && git rebase -q -X theirs origin/analises 2>/dev/null || true
  done
  cd "$GITHUB_WORKSPACE"
}
