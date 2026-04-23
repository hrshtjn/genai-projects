#!/usr/bin/env bash

# =============================================================================
# deploy.sh — Step-by-step GKE deployment for the ADK capital agent
# =============================================================================
# Run each section manually (copy-paste) so you understand what each step does.
# Do NOT run this as a single script — some steps require waiting for others.
#
# Prerequisites:
# gcloud CLI installed & authenticated (gcloud auth login)
# kubectl installed (gcloud components install kubectl)
# Project ID set below
# =============================================================================

set -euo pipefail

# ── 0. Configuration ──────────────────────────────────────────────────────────
export GOOGLE_CLOUD_PROJECT="us-con-gcp-sbx-0000467-031725"
export GOOGLE_CLOUD_LOCATION="us-east1" # project has no default VPC; existing subnet is in us-east1
export GOOGLE_GENAI_USE_VERTEXAI="true"

# Existing VPC — the project org policy disables default network creation
VPC_NETWORK="dep-it-agen14-ce-vpc"
VPC_SUBNET="dep-it-agen14-ce-vpc-sn-private-01"

# Artifact Registry repo and image tag
AR_REPO="adk-repo"
IMAGE_NAME="capital-agent"
IMAGE_TAG="latest"
IMAGE_URI="${GOOGLE_CLOUD_LOCATION}-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/${AR_REPO}/${IMAGE_NAME}:${IMAGE_TAG}"

# GKE cluster name
CLUSTER_NAME="adk-cluster"

# Kubernetes names
K8S_APP="capital-agent"
K8S_SA="adk-agent-sa" # Kubernetes service account (for Workload Identity)

# ── 1. Enable required APIs ───────────────────────────────────────────────────
# Run once per project. Safe to re-run — enabling an already-enabled API is a no-op.
gcloud services enable \
    container.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com \
    --project="${GOOGLE_CLOUD_PROJECT}"

# ── 2. Grant Cloud Build service account IAM roles ────────────────────────────
# Cloud Build uses the default Compute Engine SA. It needs these roles to:
# - Push images to Artifact Registry
# - Read source from GCS buckets
# - Write build logs
GOOGLE_CLOUD_PROJECT_NUMBER=$(
    gcloud projects describe "${GOOGLE_CLOUD_PROJECT}" \
        --format="value(projectNumber)"
)
COMPUTE_SA="${GOOGLE_CLOUD_PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for ROLE in \
    "roles/artifactregistry.writer" \
    "roles/storage.objectViewer" \
    "roles/logging.logWriter"; do
    gcloud projects add-iam-policy-binding "${GOOGLE_CLOUD_PROJECT}" \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="${ROLE}" \
        --quiet
done

# ── 3. Create GKE Autopilot cluster ───────────────────────────────────────────
# Autopilot is fully managed — no node pool configuration needed.
# Workload Identity is enabled by default in Autopilot.
# This takes ~5 minutes.
gcloud container clusters create-auto "${CLUSTER_NAME}" \
    --location="${GOOGLE_CLOUD_LOCATION}" \
    --project="${GOOGLE_CLOUD_PROJECT}" \
    --network="${VPC_NETWORK}" \
    --subnetwork="${VPC_SUBNET}"

# Connect kubectl to the new cluster
gcloud container clusters get-credentials "${CLUSTER_NAME}" \
    --location="${GOOGLE_CLOUD_LOCATION}" \
    --project="${GOOGLE_CLOUD_PROJECT}"

# Verify kubectl is pointed at the right cluster
kubectl cluster-info

# ── 4. Create Artifact Registry repository ────────────────────────────────────
gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${GOOGLE_CLOUD_LOCATION}" \
    --description="ADK learning repo" \
    --project="${GOOGLE_CLOUD_PROJECT}"

# ── 5. Build and push the container image ────────────────────────────────────
# `gcloud builds submit` uploads your source to GCS, builds in Cloud Build,
# and pushes the image to Artifact Registry — no local Docker needed.
#
# Run this from the 15_deployment/ directory (where Dockerfile lives).
cd "$(dirname "$0")" # ensure we're in 15_deployment/

gcloud builds submit \
    --tag "${IMAGE_URI}" \
    --project="${GOOGLE_CLOUD_PROJECT}" \
    .

# Verify image exists
gcloud artifacts docker images list \
    "${GOOGLE_CLOUD_LOCATION}-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/${AR_REPO}" \
    --project="${GOOGLE_CLOUD_PROJECT}"

# ── 6. Configure Workload Identity for Vertex AI access ──────────────────────
# The Kubernetes pod needs permission to call the Vertex AI API (Gemini).
# Workload Identity maps a K8s service account → GCP IAM principal.

# Create the Kubernetes service account
kubectl create serviceaccount "${K8S_SA}"

# Bind the K8s SA to the Vertex AI User role via Workload Identity
gcloud projects add-iam-policy-binding "projects/${GOOGLE_CLOUD_PROJECT}" \
    --role="roles/aiplatform.user" \
    --member="principal://iam.googleapis.com/projects/${GOOGLE_CLOUD_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${GOOGLE_CLOUD_PROJECT}.svc.id.goog/subject/ns/default/sa/${K8S_SA}" \
    --condition=None

# ── 7. Generate and apply the Kubernetes manifest ────────────────────────────
# This creates two Kubernetes resources:
# Deployment — runs our container in a Pod (replicas: 1)
# Service — exposes it as a LoadBalancer with a public IP on port 80

cat <<EOF > deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${K8S_APP}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${K8S_APP}
  template:
    metadata:
      labels:
        app: ${K8S_APP}
    spec:
      serviceAccount: ${K8S_SA}
      containers:
        - name: ${K8S_APP}
          image: ${IMAGE_URI}
          imagePullPolicy: Always
          resources:
            limits:
              memory: "512Mi"
              cpu: "500m"
              ephemeral-storage: "512Mi"
            requests:
              memory: "256Mi"
              cpu: "250m"
              ephemeral-storage: "256Mi"
          ports:
            - containerPort: 8080
          env:
            - name: PORT
              value: "8080"
            - name: GOOGLE_CLOUD_PROJECT
              value: ${GOOGLE_CLOUD_PROJECT}
            - name: GOOGLE_CLOUD_LOCATION
              value: ${GOOGLE_CLOUD_LOCATION}
            - name: GOOGLE_GENAI_USE_VERTEXAI
              value: "${GOOGLE_GENAI_USE_VERTEXAI}"
---
apiVersion: v1
kind: Service
metadata:
  name: ${K8S_APP}
spec:
  type: LoadBalancer
  ports:
    - port: 80
      targetPort: 8080
  selector:
    app: ${K8S_APP}
EOF

kubectl apply -f deployment.yaml

# ── 8. Wait for the pod and get the external IP ───────────────────────────────
echo "Waiting for pod to be Running..."
kubectl rollout status deployment/${K8S_APP}

echo "Waiting for external IP (may take 2-3 minutes)..."
kubectl get service ${K8S_APP} --watch

# Get external IP once assigned
EXTERNAL_IP=$(kubectl get svc ${K8S_APP} -o=jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo ""
echo "✅ Agent deployed at: http://${EXTERNAL_IP}"
echo " Dev UI: http://${EXTERNAL_IP}/dev-ui/"
echo ""

# ── 9. Test with curl ─────────────────────────────────────────────────────────
APP_URL="http://${EXTERNAL_IP}"

# List available agents
curl -s "${APP_URL}/list-apps" | python3 -m json.tool

# Create a session
curl -s -X POST \
    "${APP_URL}/apps/gke_agent_01/users/test_user/sessions" \
    -H "Content-Type: application/json" \
    -d '{"state": {}}' | python3 -m json.tool

# (Copy session_id from above output, then replace SESSION_ID below)
SESSION_ID="your-session-id-here"

# Run the agent
curl -s -X POST "${APP_URL}/run" \
    -H "Content-Type: application/json" \
    -d "{
\"app_name\": \"gke_agent_01\",
\"user_id\": \"test_user\",
\"session_id\": \"${SESSION_ID}\",
\"new_message\": {
\"role\": \"user\",
\"parts\": [{\"text\": \"What is the capital of France?\"}]
},
\"streaming\": false
}" | python3 -m json.tool

# ── Option 2: One command automated deployment ────────────────────────────────
# After completing steps 1-4 (APIs, cluster, IAM, Artifact Registry),
# you can skip steps 5-8 and use this single command instead:
#
# adk deploy gke \
#   --project "${GOOGLE_CLOUD_PROJECT}" \
#   --cluster_name "${CLUSTER_NAME}" \
#   --region "${GOOGLE_CLOUD_LOCATION}" \
#   --with_ui \
#   --log_level info \
#   .
#
# This builds the image, pushes it, generates manifests, and deploys — all in one step.

# ── 10. Cleanup ───────────────────────────────────────────────────────────────
# Uncomment to tear down all resources when done learning.

# kubectl delete -f deployment.yaml

# gcloud container clusters delete "${CLUSTER_NAME}" \
#   --location="${GOOGLE_CLOUD_LOCATION}" \
#   --project="${GOOGLE_CLOUD_PROJECT}" \
#   --quiet

# gcloud artifacts repositories delete "${AR_REPO}" \
#   --location="${GOOGLE_CLOUD_LOCATION}" \
#   --project="${GOOGLE_CLOUD_PROJECT}" \
#   --quiet
