#!/usr/bin/env bash
# Deploy the live Compass agent to Google Cloud Run for a demo, at ~$0/month.
#
# Run in Google Cloud Shell (shell.cloud.google.com), from the repo folder:
#   git clone https://github.com/Ai-Prince-1/-walmart-agentic-compass.git
#   cd -- -walmart-agentic-compass && bash deploy/cloudrun.sh
#
# What it does
#   - Stores your Gemini API key in Secret Manager (never in code or in the image)
#   - Optionally stores a demo passcode the same way
#   - Deploys with 0 minimum instances (no cost while idle) and 1 maximum
#     instance (caps spend), plus the app's own daily request cap
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-agentic-compass}"
DAILY_CAP="${DAILY_CAP:-200}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "No Google Cloud project selected. Run: gcloud config set project YOUR_PROJECT_ID"; exit 1
fi
echo "Project: $PROJECT_ID   Region: $REGION   Service: $SERVICE"

gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com --quiet

put_secret () {  # name, prompt
  local name="$1" value
  read -r -s -p "$2: " value; echo
  [[ -z "$value" ]] && return 1
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=- >/dev/null
  else
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=- --replication-policy=automatic >/dev/null
  fi
  echo "  saved $name in Secret Manager"
}

if gcloud secrets describe compass-gemini-key >/dev/null 2>&1; then
  read -r -p "A Gemini key is already stored. Replace it? [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] && put_secret compass-gemini-key "Paste your Gemini API key (hidden)"
else
  put_secret compass-gemini-key "Paste your Gemini API key (hidden)" || { echo "A key is required."; exit 1; }
fi

SECRETS="GOOGLE_API_KEY=compass-gemini-key:latest"
read -r -p "Protect the demo with a passcode? [Y/n] " ans
if [[ ! "$ans" =~ ^[Nn]$ ]]; then
  put_secret compass-demo-passcode "Choose a demo passcode (hidden)" && SECRETS="$SECRETS,DEMO_PASSCODE=compass-demo-passcode:latest"
fi

# Let Cloud Run's runtime identity read the secrets
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
for s in compass-gemini-key compass-demo-passcode; do
  gcloud secrets describe "$s" >/dev/null 2>&1 && gcloud secrets add-iam-policy-binding "$s" \
    --member="serviceAccount:${RUNTIME_SA}" --role=roles/secretmanager.secretAccessor --quiet >/dev/null
done

gcloud run deploy "$SERVICE" --source . --region "$REGION" --quiet \
  --allow-unauthenticated \
  --min-instances 0 --max-instances 1 \
  --memory 1Gi --cpu 1 --timeout 120 \
  --set-env-vars "DAILY_REQUEST_CAP=${DAILY_CAP}" \
  --set-secrets "$SECRETS"

URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
echo
echo "Live at: $URL"
echo "Next: in GitHub, Settings -> Secrets and variables -> Actions -> Variables,"
echo "      add COMPASS_LIVE_URL = $URL   (powers the demo button and the monthly check)"
