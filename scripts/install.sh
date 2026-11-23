#!/bin/sh
# Install the Credenzo binary from a GitHub release.
#
#   curl -fsSL https://raw.githubusercontent.com/adudley78/credenzo/main/scripts/install.sh | sh
#
# Settings (environment):
#   CREDENZO_VERSION      release tag to install, e.g. v0.36.1 (default: the latest release)
#   CREDENZO_INSTALL_DIR  where to put the binary (default: /usr/local/bin)
#   CREDENZO_SKIP_VERIFY  set to 1 to install without the build-provenance check
#
# The binary is checked with `gh attestation verify` against the release
# workflow, as setup-action does. Without `gh`, or when the check fails,
# nothing is installed unless CREDENZO_SKIP_VERIFY=1. POSIX sh: no bash needed.
set -eu

REPO="adudley78/credenzo"
INSTALL_DIR="${CREDENZO_INSTALL_DIR:-/usr/local/bin}"

fail() {
    echo "credenzo install: $*" >&2
    exit 1
}

case "$(uname -s)" in
    Darwin) OS=darwin ;;
    Linux) OS=linux ;;
    *) fail "no binary for $(uname -s); use: pip install mcp-audit-scanner" ;;
esac
case "$(uname -m)" in
    x86_64 | amd64) ARCH=x86_64 ;;
    arm64 | aarch64) ARCH=arm64 ;;
    *) fail "no binary for $(uname -m); use: pip install mcp-audit-scanner" ;;
esac
if [ "$OS" = linux ] && [ "$ARCH" = arm64 ]; then
    fail "no Linux arm64 binary; use: pip install mcp-audit-scanner"
fi

VERSION="${CREDENZO_VERSION:-}"
if [ -z "$VERSION" ]; then
    # github.com/<repo>/releases/latest redirects to .../releases/tag/<tag>.
    LATEST=$(curl -fsSLI -o /dev/null -w '%{url_effective}' \
        "https://github.com/${REPO}/releases/latest") || fail "could not find the latest release"
    VERSION="${LATEST##*/}"
fi
case "$VERSION" in
    v[0-9]*) ;;
    *) fail "not a release tag: $VERSION" ;;
esac

BINARY="mcp-audit-${OS}-${ARCH}"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT INT TERM

echo "Downloading Credenzo ${VERSION} for ${OS}/${ARCH}..."
curl -fsSL --retry 3 -o "$TMP/$BINARY" \
    "https://github.com/${REPO}/releases/download/${VERSION}/${BINARY}" \
    || fail "download failed: ${VERSION}/${BINARY}"

if [ "${CREDENZO_SKIP_VERIFY:-}" = 1 ]; then
    echo "WARNING: CREDENZO_SKIP_VERIFY=1: the build provenance is not checked." >&2
elif ! command -v gh >/dev/null 2>&1; then
    fail "the GitHub CLI (gh) is needed to check the build provenance. Install it, or set CREDENZO_SKIP_VERIFY=1 to install without the check."
elif ! gh attestation verify "$TMP/$BINARY" --repo "$REPO" \
        --signer-workflow "${REPO}/.github/workflows/release.yml" >/dev/null; then
    fail "${BINARY} ${VERSION} failed the build-provenance check. Do not run it; report it at https://github.com/${REPO}/security"
fi

chmod 0755 "$TMP/$BINARY"
mkdir -p "$INSTALL_DIR"
mv -f "$TMP/$BINARY" "$INSTALL_DIR/credenzo"

# The old command name keeps working. An existing mcp-audit that is not a link
# (a pip install) is left alone.
if [ -L "$INSTALL_DIR/mcp-audit" ] || [ ! -e "$INSTALL_DIR/mcp-audit" ]; then
    ln -sf "$INSTALL_DIR/credenzo" "$INSTALL_DIR/mcp-audit"
else
    echo "Left $INSTALL_DIR/mcp-audit as it is (not a link); use 'credenzo'."
fi

echo "Installed credenzo to $INSTALL_DIR/credenzo"
CREDENZO_NO_STAR_PROMPT=1 "$INSTALL_DIR/credenzo" version
echo
echo "Next: run 'credenzo check' for a one-page verdict on this machine."
echo "Credenzo is free and open source. A star helps other teams find it:"
echo "  https://github.com/${REPO}"
