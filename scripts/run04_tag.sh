# ...existing code...
#!/usr/bin/env bash
set -euo pipefail

# このスクリプトは「直接実行」すること（source しない）
if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: このスクリプトは source ではなく直接実行してください:\n  ./run04_tag.sh\n' >&2
    return 1 2>/dev/null || exit 1
fi

cd "$(dirname "$0")" || exit 1

if ! command -v git >/dev/null 2>&1; then
    echo "[Error] git が見つかりません。" >&2
    exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[Error] このディレクトリは Git リポジトリではありません。" >&2
    exit 1
fi

CUR_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
CUR_BRANCH="${CUR_BRANCH:-main}"
LATEST_TAG="$(git tag --sort=-version:refname 2>/dev/null | head -n1 || true)"
LATEST_TAG="${LATEST_TAG:-v0.0.0}"

cat <<EOF
========================================
           Git Tag Script
========================================
Current branch : $CUR_BRANCH
Latest tag     : $LATEST_TAG

EOF

read -r -p "Please enter NEW tag version (ex: v1.2.3): " VERSION
if [ -z "${VERSION// /}" ]; then
    echo "[Error] Version cannot be empty." >&2
    exit 1
fi

# Ensure tag doesn't already exist
if git rev-parse -q --verify "refs/tags/$VERSION" >/dev/null 2>&1; then
    echo "[Error] Tag $VERSION already exists." >&2
    exit 1
fi

read -r -p "Enter tag message (annotation): " TAG_MSG
if [ -z "${TAG_MSG// /}" ]; then
    echo "[Error] Tag message cannot be empty." >&2
    exit 1
fi
TAG_MSG="${TAG_MSG//\"/\'}"

echo "Creating annotated tag $VERSION ..."
if ! git tag -a "$VERSION" -m "$TAG_MSG"; then
    echo "[Error] Tag creation failed." >&2
    exit 1
fi

echo "Pushing tag $VERSION to origin ..."
if ! git push origin "$VERSION"; then
    echo "[Error] Tag push failed." >&2
    exit 1
fi

echo
echo "[Success] Tag $VERSION created and pushed."
exit 0
# ...existing code...