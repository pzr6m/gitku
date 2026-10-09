#!/usr/bin/env bash
# Build a small, fully fictional git repository that contains every kind of
# haiku gitku can find. Used for the README examples and for trying gitku out:
#
#   bash examples/make_demo_repo.sh /tmp/gitku-demo
#   gitku /tmp/gitku-demo
set -euo pipefail

dest="${1:?usage: make_demo_repo.sh DIR}"
mkdir -p "$dest"
cd "$dest"
git init -q -b main

export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null

# commit AUTHOR DATE MESSAGE  (stages whatever is already in the work tree)
commit() {
  local name="$1" date="$2" msg="$3"
  local email
  email="$(echo "${name%% *}" | tr '[:upper:]' '[:lower:]')@example.com"
  git add -A
  GIT_AUTHOR_NAME="$name" GIT_AUTHOR_EMAIL="$email" GIT_AUTHOR_DATE="${date}T12:00:00+00:00" \
  GIT_COMMITTER_NAME="$name" GIT_COMMITTER_EMAIL="$email" GIT_COMMITTER_DATE="${date}T12:00:00+00:00" \
    git -c commit.gpgsign=false commit --allow-empty -q -m "$msg"
}

commit "Ada Lovelace" 2025-03-04 "the build is broken nobody touched the config and yet here we are"
commit "Ada Lovelace" 2025-03-05 $'the old cache is gone\nwe cleared it out of our disks\nspace returns to us'
commit "Linus Example" 2025-03-06 $'stop the retry loop before it eats the whole queue or we all lose sleep\n\nCo-Authored-By: Grace Hopper <grace@example.com>'
commit "Linus Example" 2025-03-07 "update dependencies"
commit "Ada Lovelace" 2025-03-10 $'friday deploy fails\ntests were green but prod was not\nrollback and breathe deep'
commit "Grace Hopper" 2025-03-12 $'tidy retry logic\n\nCleaned up retries. The logs are quiet, the pager sleeps through the night, and nobody weeps.'

cat > README.md <<'EOF'
# Demo project

quiet morning light
settles on the sleeping town
coffee warms my hands
EOF
cat > cache.py <<'EOF'
def get(key):
    return _CACHE.get(key)

# never trust the cache it lies to you when you least expect it again
_CACHE = {}
EOF
commit "Grace Hopper" 2025-03-14 "add readme and a tiny cache"
commit "Linus Example" 2025-03-20 "bump version"

echo "demo repository created in $dest"
