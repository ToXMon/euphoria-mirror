#!/usr/bin/env bash
# Kronos Edge — Akash GPU Deployment Script
# Prerequisites: akash + provider-services CLI installed, wallet funded

set -euo pipefail

SDL_FILE="${SDL_FILE:-$(dirname "$0")/../sdl/gpu-inference.yaml}"
KEY_NAME="${KEY_NAME:-default}"
CHAIN_ID="${CHAIN_ID:-akashnet-2}"
NODE="${NODE:-https://rpc.akash.cloudqr.io:443}"

echo "=== Kronos Edge — Akash Deployment ==="
echo "SDL: $SDL_FILE"
echo "Key: $KEY_NAME"
echo ""

# Step 1: Create certificate if not exists
 echo "[1/4] Checking certificate..."
CERT_OUTPUT=$(provider-services query cert list --owner "$(provider-services keys show "$KEY_NAME" -a)" 2>&1 || true)
if echo "$CERT_OUTPUT" | grep -q "certificate"; then
  echo "Certificate already exists. Skipping creation."
else
  echo "Creating certificate..."
  provider-services tx cert create client --from "$KEY_NAME" --chain-id "$CHAIN_ID" --node "$NODE" -y
  echo "Certificate created."
fi
echo ""

# Step 2: Create deployment
echo "[2/4] Creating deployment..."
DEPLOY_OUTPUT=$(provider-services tx deployment create "$SDL_FILE" --from "$KEY_NAME" --chain-id "$CHAIN_ID" --node "$NODE" -y 2>&1)
DSEQ=$(echo "$DEPLOY_OUTPUT" | grep -oP 'dseq: \K[0-9]+' || echo "")

if [ -z "$DSEQ" ]; then
  echo "ERROR: Failed to create deployment. Output:"
  echo "$DEPLOY_OUTPUT"
  exit 1
fi
echo "Deployment created. DSEQ: $DSEQ"
echo ""

# Step 3: Wait for bids
echo "[3/4] Waiting for bids (30s)..."
sleep 30

# Get provider with lowest bid
echo "Querying bids..."
BID_OUTPUT=$(provider-services query bid list --owner "$(provider-services keys show "$KEY_NAME" -a)" --dseq "$DSEQ" 2>&1)
PROVIDER=$(echo "$BID_OUTPUT" | grep -oP 'provider: \K[^\s]+' | head -1)

if [ -z "$PROVIDER" ]; then
  echo "ERROR: No bids received. Check SDL pricing and wallet balance."
  exit 1
fi
echo "Selected provider: $PROVIDER"

# Accept bid / create lease
echo "Creating lease..."
provider-services tx lease create --owner "$(provider-services keys show "$KEY_NAME" -a)" --dseq "$DSEQ" --provider "$PROVIDER" --from "$KEY_NAME" --chain-id "$CHAIN_ID" --node "$NODE" -y
echo ""

# Step 4: Send manifest
echo "[4/4] Sending manifest..."
provider-services send-manifest "$SDL_FILE" --dseq "$DSEQ" --provider "$PROVIDER" --from "$KEY_NAME" --chain-id "$CHAIN_ID" --node "$NODE"
echo "Manifest sent."
echo ""

# Output lease info
echo "=== Deployment Active ==="
echo "DSEQ:     $DSEQ"
echo "Provider: $PROVIDER"
echo "SDL:      $SDL_FILE"
echo ""
echo "Query status:"
echo "  provider-services query lease list --owner \$(provider-services keys show $KEY_NAME -a) --dseq $DSEQ"
echo ""
echo "Get service URI:"
echo "  provider-services lease-status --dseq $DSEQ --provider $PROVIDER --from $KEY_NAME"
