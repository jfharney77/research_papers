# Deploying to AWS (ECS Express Mode + GitHub Actions)

This deploys the **product** (the `docserver` FastAPI backend + the `web` React/Vite
frontend) as two AWS **ECS Express Mode** services. ECS Express gives each service a
load balancer, autoscaling, and HTTPS automatically; you just hand it a container image.
(App Runner is being retired, so we use ECS Express.)

```
GitHub Actions ──build+push──▶ ECR ──▶ ECS Express service (backend)  https://cl-….ecs.<region>.on.aws  →  /health
                                  └──▶ ECS Express service (frontend) https://cl-….ecs.<region>.on.aws
```

Two Dockerfiles are already in the repo: `docker/backend.Dockerfile` (Python + TeX Live)
and `web/Dockerfile` (Vite build → static `serve`). The workflow is `.github/workflows/deploy-aws.yml`.

> Replace `<ACCOUNT_ID>` and `<REGION>` (e.g. `us-east-1`) throughout. Keep **one region** for ECR + ECS.

---

## Prerequisites
- AWS account + AWS CLI v2 logged in (`aws sts get-caller-identity` works), and **Docker or Podman** locally for the first manual push.
- This repo on GitHub (`jfharney77/research_papers`).

> **Docker or Podman?** Both Dockerfiles build and run unchanged with either. The commands below use `docker`, but `podman` is a drop-in — `podman build`, `podman push`, and `aws ecr get-login-password | podman login --username AWS --password-stdin <ecr>` all take the same flags. Both images have been verified to build and run locally with Podman (backend `/health` OK with TeX Live present; frontend serves; auth enforced when `DOCSERVER_API_KEY` is set).

## Step 1 — ECR repositories
```bash
aws ecr create-repository --repository-name research-papers-backend  --region <REGION>
aws ecr create-repository --repository-name research-papers-frontend --region <REGION>
```

## Step 2 — Two IAM roles ECS needs
**Task execution role** (pull images, write logs):
```bash
aws iam create-role --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```
**Infrastructure role** (provision ALB/SGs/networking):
```bash
aws iam create-role --role-name ecsInfrastructureRoleForExpressServices \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name ecsInfrastructureRoleForExpressServices \
  --policy-arn arn:aws:iam::aws:policy/AmazonECSInfrastructureRoleForExpressGatewayServices
```

## Step 3 — GitHub OIDC deploy role (no long-lived keys)
Add GitHub as an OIDC provider (skip if it already exists):
```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```
Create the role GitHub Actions assumes (trusts the repo's `deploy-aws` branch):
```bash
aws iam create-role --role-name research-papers-deploy \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Principal":{"Federated":"arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"},
      "Action":"sts:AssumeRoleWithWebIdentity",
      "Condition":{
        "StringEquals":{"token.actions.githubusercontent.com:aud":"sts.amazonaws.com"},
        "StringLike":{"token.actions.githubusercontent.com:sub":"repo:jfharney77/research_papers:ref:refs/heads/deploy-aws"}
      }
    }]
  }'
aws iam attach-role-policy --role-name research-papers-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
aws iam put-role-policy --role-name research-papers-deploy --policy-name ecr-and-passrole \
  --policy-document '{
    "Version":"2012-10-17",
    "Statement":[
      {"Effect":"Allow","Action":["ecr:GetAuthorizationToken","ecr:BatchCheckLayerAvailability","ecr:PutImage","ecr:InitiateLayerUpload","ecr:UploadLayerPart","ecr:CompleteLayerUpload","ecr:BatchGetImage"],"Resource":"*"},
      {"Effect":"Allow","Action":"iam:PassRole","Resource":[
        "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
        "arn:aws:iam::<ACCOUNT_ID>:role/ecsInfrastructureRoleForExpressServices"]}
    ]
  }'
```
The role ARN is `arn:aws:iam::<ACCOUNT_ID>:role/research-papers-deploy`.
*(No OIDC? Fall back to an IAM user with the same two policies and store `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` as secrets, swapping the `configure-aws-credentials` inputs.)*

## Step 4 — First deploy by hand (the VITE chicken-and-egg)
Pick a strong API key once: `export KEY=$(openssl rand -hex 24)`

```bash
ACCT=<ACCOUNT_ID>; REGION=<REGION>; ECR=$ACCT.dkr.ecr.$REGION.amazonaws.com
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR

# 4a. Backend image (from repo root)
docker build -f docker/backend.Dockerfile -t $ECR/research-papers-backend:latest .
docker push $ECR/research-papers-backend:latest

# 4b. Create the backend service (auth on, CORS opened later)
aws ecs create-express-gateway-service \
  --service-name research-papers-backend \
  --primary-container "{\"image\":\"$ECR/research-papers-backend:latest\",\"containerPort\":8080,\"environment\":[{\"name\":\"DOCSERVER_API_KEY\",\"value\":\"$KEY\"},{\"name\":\"LATEX_SANDBOX\",\"value\":\"local\"}]}" \
  --execution-role-arn arn:aws:iam::$ACCT:role/ecsTaskExecutionRole \
  --infrastructure-role-arn arn:aws:iam::$ACCT:role/ecsInfrastructureRoleForExpressServices \
  --health-check-path /health --region $REGION
# → note ingressPaths[0].endpoint  →  BACKEND_URL

# 4c. Frontend image — bake in the backend URL and the token
docker build --build-arg VITE_API_BASE=<BACKEND_URL> --build-arg VITE_DOCSERVER_TOKEN=$KEY \
  -f web/Dockerfile -t $ECR/research-papers-frontend:latest web
docker push $ECR/research-papers-frontend:latest

aws ecs create-express-gateway-service \
  --service-name research-papers-frontend \
  --primary-container "{\"image\":\"$ECR/research-papers-frontend:latest\",\"containerPort\":8080}" \
  --execution-role-arn arn:aws:iam::$ACCT:role/ecsTaskExecutionRole \
  --infrastructure-role-arn arn:aws:iam::$ACCT:role/ecsInfrastructureRoleForExpressServices \
  --region $REGION
# → note ingressPaths[0].endpoint  →  FRONTEND_URL

# 4d. Open backend CORS to the frontend origin (use the backend service ARN).
#     Optionally enable Claude here too: add CRITIC_PROVIDER=claude + ANTHROPIC_API_KEY.
aws ecs update-express-gateway-service --service-arn <BACKEND_SERVICE_ARN> \
  --primary-container "{\"image\":\"$ECR/research-papers-backend:latest\",\"containerPort\":8080,\"environment\":[{\"name\":\"DOCSERVER_API_KEY\",\"value\":\"$KEY\"},{\"name\":\"DOCSERVER_CORS_ORIGINS\",\"value\":\"<FRONTEND_URL>\"},{\"name\":\"LATEX_SANDBOX\",\"value\":\"local\"},{\"name\":\"CRITIC_PROVIDER\",\"value\":\"claude\"},{\"name\":\"ANTHROPIC_API_KEY\",\"value\":\"<ANTHROPIC_API_KEY>\"}]}" \
  --region $REGION
```
Open `<FRONTEND_URL>` — the app should load and talk to the backend.

## Step 5 — GitHub repo settings (Settings → Secrets and variables → Actions)
**Variables:** `AWS_REGION`, `AWS_ACCOUNT_ID`, `BACKEND_URL` (from 4b), `FRONTEND_URL` (from 4c), `CRITIC_PROVIDER` (`claude` to enable Claude, else leave blank for the offline stub)
**Secrets:** `AWS_DEPLOY_ROLE_ARN` (from Step 3), `DOCSERVER_API_KEY` (`$KEY`), `BACKEND_SERVICE_ARN`, `FRONTEND_SERVICE_ARN`, `ANTHROPIC_API_KEY` (only if using Claude)

## Step 6 — Automated deploys
```bash
git checkout -b deploy-aws && git push -u origin deploy-aws
```
Every push to `deploy-aws` (or a manual **Run workflow**) builds, pushes, and rolls both
services. Flip the `on.push.branches` in the workflow to your default branch when ready.

---

## Notes & caveats
- **Backend image is large (~2 GB)** because it bundles TeX Live for all four templates. First build/push is slow; trim the `apt-get` list in `docker/backend.Dockerfile` if you only need one template.
- **Local disk is ephemeral.** `documents/` (converted workspaces, built PDFs, `critique.json`) lives in the task and is lost on redeploy/scale. For persistence, attach **EFS** to the service or move artifacts to S3.
- **Critic providers:** the `anthropic` SDK is already baked into the backend image (the Dockerfile installs the `llm` extra). To use **Claude** in the deployed app, set the backend service env `CRITIC_PROVIDER=claude` and `ANTHROPIC_API_KEY=<your key>` — the CI workflow wires these from the `CRITIC_PROVIDER` variable and `ANTHROPIC_API_KEY` secret. Leave `CRITIC_PROVIDER` unset (or `stub`) to run the offline analyzer. If the key is missing or invalid, the provider degrades to the stub rather than failing. Ollama isn't reachable from AWS unless you expose it.
- **Never** run `aws ecs update-service` against these services — only `*-express-gateway-service` APIs. Mixing them corrupts the deployment state (recover by `delete-express-gateway-service` + recreate).
