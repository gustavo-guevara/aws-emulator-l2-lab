# Point the AWS CLI and SDKs at the local AWS Emulator.
# Usage:  source scripts/env.sh          (default port 9297)
#         EMU_PORT=9300 source scripts/env.sh
# Must be *sourced*, not executed, so the variables stay in your shell.

EMU_PORT="${EMU_PORT:-9297}"
EMU_DIR="$HOME/.aws/emulator/$EMU_PORT"

export AWS_ENDPOINT_URL="https://127.0.0.1:$EMU_PORT"
export AWS_SHARED_CREDENTIALS_FILE="$EMU_DIR/emulator_credentials"
export AWS_CONFIG_FILE="$EMU_DIR/config"
export AWS_CA_BUNDLE="$EMU_DIR/ca.pem"
export AWS_EC2_METADATA_DISABLED=true
export AWS_DISABLE_HOST_PREFIX_INJECTION=true
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
# Never let real credentials leak into the lab.
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_PROFILE
# Corporate proxies must not intercept local traffic.
export NO_PROXY="127.0.0.1,localhost${NO_PROXY:+,$NO_PROXY}"
export no_proxy="$NO_PROXY"

if [ ! -f "$AWS_CA_BUNDLE" ]; then
  echo "WARNING: $AWS_CA_BUNDLE not found. Is aws-emulator running on port $EMU_PORT?"
else
  echo "OK: AWS calls now go to $AWS_ENDPOINT_URL"
fi
