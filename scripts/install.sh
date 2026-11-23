#!/usr/bin/env bash
# Install AWS Emulator, AWS CLI v2 and the Python environment inside the VM.
# Works on Ubuntu amd64 and arm64 (Apple Silicon Macs give you arm64 VMs).
set -euo pipefail

ARCH="$(dpkg --print-architecture)"   # amd64 or arm64
case "$ARCH" in
  amd64) CLI_ARCH="x86_64" ;;
  arm64) CLI_ARCH="aarch64" ;;
  *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac
echo "==> Architecture: $ARCH"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if ! command -v aws-emulator >/dev/null; then
  echo "==> Installing AWS Emulator"
  curl -fsSLo "$TMP/aws-emulator.deb" \
    "https://downloads.aws.com/aws-emulator/packages/aws-emulator/LTS/latest/aws-emulator_${ARCH}.deb"
  sudo apt-get install -y "$TMP/aws-emulator.deb"
fi
aws-emulator -v

if ! command -v aws >/dev/null; then
  echo "==> Installing AWS CLI v2"
  curl -fsSLo "$TMP/awscliv2.zip" "https://awscli.amazonaws.com/awscli-exe-linux-${CLI_ARCH}.zip"
  unzip -q "$TMP/awscliv2.zip" -d "$TMP"
  sudo "$TMP/aws/install"
fi
aws --version

# Keep the virtualenv outside the mounted folder; mounts from macOS are slow for venvs.
VENV="$HOME/.venv-lab"
if [ ! -d "$VENV" ]; then
  echo "==> Creating Python virtualenv at $VENV"
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$(dirname "$0")/../requirements.txt"

echo
echo "Done. Next:"
echo "  Terminal 1:  aws-emulator"
echo "  Terminal 2:  source ~/.venv-lab/bin/activate && source scripts/env.sh"
