# Deploying AG-UI Chat POC to Google Kubernetes Engine (GKE)

This guide provides step-by-step instructions to build, containerize, and deploy the AG-UI Chat POC (Agent, Runtime, and Frontend) to a Google Kubernetes Engine (GKE) cluster. It also includes Workload Identity setup to seamlessly authenticate with Vertex AI.

## Prerequisites

1. A [Google Cloud Platform (GCP)](https://cloud.google.com/) account with an active billing project.
2. [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed.
3. [`kubectl`](https://kubernetes.io/docs/tasks/tools/) installed.

---

## Step 1: Set Up Your GCP Environment

Open your terminal and authenticate with Google Cloud. Set your project ID and enable the necessary APIs.

```bash
# 1. Login to Google Cloud
gcloud auth login

# 2. Set your active project and variables
export PROJECT_ID="project-2db91b7b-2a47-4e55-b14" 
export REGION="us-central1"
export ZONE="us-central1-a"
export REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/agui-repo"

gcloud config set project $PROJECT_ID

# 3. Enable needed APIs
gcloud services enable container.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
```

---

## Step 2: Create the GKE Cluster with Workload Identity

Create a standard Kubernetes cluster and enable Workload Identity. Workload Identity is the recommended way to allow your GKE pods to authenticate securely to Google APIs (like Vertex AI) without needing rotating API keys.

```bash
# Create the cluster with workload identity enabled
gcloud container clusters create agui-cluster \
    --zone $ZONE \
    --num-nodes 1 \
    --workload-pool="${PROJECT_ID}.svc.id.goog"

# Ensure the default node pool has metadata server enabled
gcloud container node-pools update default-pool \
    --cluster=agui-cluster \
    --zone=$ZONE \
    --workload-metadata=GKE_METADATA

# Configure kubectl to connect to your new cluster
gcloud container clusters get-credentials agui-cluster --zone $ZONE
```

---

## Step 3: Configure Workload Identity for Vertex AI

Your agent pod needs permission to use Vertex AI. We map a Kubernetes Service Account (KSA) to a Google Service Account (GSA).

```bash
# 1. Create a Google Service Account (GSA)
gcloud iam service-accounts create agui-agent-sa \
    --project=$PROJECT_ID \
    --description="Agent SA with Vertex AI access"

# 2. Grant the GSA the Vertex AI User Role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:agui-agent-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# 3. Bind the KSA to the GSA
gcloud iam service-accounts add-iam-policy-binding "agui-agent-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:${PROJECT_ID}.svc.id.goog[default/agui-agent-ksa]"
```

---

## Step 4: Set Up Google Artifact Registry (GAR)

Create a repository to store your Docker images.

```bash
# Create a Docker repository named 'agui-repo'
gcloud artifacts repositories create agui-repo \
    --repository-format=docker \
    --location=$REGION \
    --description="Docker repository for AG-UI Chat images"
```

---

## Step 5: Ignore Dependencies & Build Images via Cloud Build

To keep builds fast, we use `.gcloudignore` files to prevent uploading massive `node_modules`/`.venv` folders.

```bash
# Ensure local environments are ignored
echo -e ".venv\n.env\n__pycache__\n*.pyc" > agent/.gcloudignore
echo -e "node_modules\ndist\n.env\n.DS_Store" > runtime/.gcloudignore
echo -e "node_modules\ndist\n.env\n.DS_Store" > frontend/.gcloudignore

# Build and Push using Cloud Build (No local Docker needed!)
gcloud builds submit --tag ${REPO}/agent:latest ./agent
gcloud builds submit --tag ${REPO}/runtime:latest ./runtime
gcloud builds submit --tag ${REPO}/frontend:latest ./frontend
```

---

## Step 6: Deploy to GKE

Apply the manifests to your Kubernetes cluster. Our configuration (`k8s-manifests.yaml`) includes:
- Workload Identity mapping (`agui-agent-ksa`) for the Agent.
- Correct load-balancer routing paths (`/*` vs `/copilotkit`).
- **BackendConfig** to ensure the Load Balancer routes health checks specifically to `/health` on the Runtime pod (preventing 502 errors).

```bash
kubectl apply -f k8s-manifests.yaml
```

Verify everything is running successfully:
```bash
# Check if pods are running
kubectl get pods

# Check if services are created
kubectl get svc
```

---

## Step 7: Access the Application

Google Cloud will provision a Load Balancer for your Ingress. This process can take 5-10 minutes.

Check the status of your Ingress:

```bash
kubectl get ingress agui-ingress --watch
```

Wait until an IP address appears in the `ADDRESS` column:
```text
NAME           CLASS   HOSTS   ADDRESS          PORTS   AGE
agui-ingress   gce     *       34.111.1.177     80      2m
```

Once the address is populated, open your web browser and navigate to:
**`http://<YOUR_INGRESS_IP>`**

*Note: It may take an additional 3-5 minutes after the IP appears for the Load Balancer health checks to propagate and return a `HEALTHY` status.*

---

## Clean Up (Optional)

To avoid incurring ongoing charges for the cluster and resources when you are done:

```bash
gcloud container clusters delete agui-cluster --zone $ZONE --quiet
gcloud artifacts repositories delete agui-repo --location=$REGION --quiet
```

# For Python Agent Logs
kubectl logs -f deployment/agent-deployment

# For Node.js Runtime Logs
kubectl logs -f deployment/runtime-deployment
