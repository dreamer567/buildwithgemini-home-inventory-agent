#!/usr/bin/env bash
# ==============================================================================
# 🏠 3LDK Home Inventory Butler - One-Click Self-Hosted GCP Deploy Script
# ==============================================================================
# Usage:
#   ./deploy_to_my_gcp.sh [YOUR_PROJECT_ID] [REGION]
#
# Examples:
#   ./deploy_to_my_gcp.sh my-personal-gcp-project us-east1
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}  🏠 3LDK 家居收纳与生活采购智能管家 - 个人 GCP 一键自动化部署脚本      ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Resolve Target Project ID & Region
PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null || echo "")}"
REGION="${2:-us-east1}"

if [ -z "$PROJECT_ID" ]; then
  echo -e "${RED}[ERROR] 未指定 GCP 项目 ID！${NC}"
  echo "使用方法: ./deploy_to_my_gcp.sh <YOUR_GCP_PROJECT_ID> [REGION]"
  exit 1
fi

echo -e "${GREEN}✓ 目标 GCP 项目:${NC} ${PROJECT_ID}"
echo -e "${GREEN}✓ 部署区域 Region:${NC} ${REGION}"

gcloud config set project "$PROJECT_ID"

# 2. Enable Required GCP APIs
echo -e "\n${YELLOW}▶ [1/6] 正在启用 Google Cloud 依赖 API 服务...${NC}"
gcloud services enable \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  run.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

# 3. Create Cloud Storage Bucket for Multi-modal Media
BUCKET_NAME="home-inventory-media-${PROJECT_ID}"
echo -e "\n${YELLOW}▶ [2/6] 正在配置 Cloud Storage 存储桶 (用于存放生图与短视频): gs://${BUCKET_NAME} ...${NC}"
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" &>/dev/null; then
  gcloud storage buckets create "gs://${BUCKET_NAME}" --location="${REGION}"
fi

# Set public read access for media delivery
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="allUsers" \
  --role="roles/storage.objectViewer" || true

# 4. Create Firestore Native Database & Seed Inventory
echo -e "\n${YELLOW}▶ [3/6] 正在检查与配置 Cloud Firestore 原生模式数据库...${NC}"
if ! gcloud firestore databases list --format="value(name)" 2>/dev/null | grep -q "(default)"; then
  echo "正在初始化创建 (default) 原生模式 Firestore 数据库..."
  gcloud firestore databases create --location="${REGION}" --type=firestore-native
else
  echo -e "${GREEN}✓ Firestore 数据库已就绪${NC}"
fi

echo -e "\n${YELLOW}▶ [4/6] 正在灌入 3LDK 初始收纳与食材库存数据...${NC}"
GOOGLE_CLOUD_PROJECT="$PROJECT_ID" python3 scripts/seed_firestore.py

# 5. Deploy Agent to Vertex AI Agent Engine
echo -e "\n${YELLOW}▶ [5/6] 正在打包并部署 Agent 至 Vertex AI Agent Engine...${NC}"
if ! command -v agents-cli &>/dev/null; then
  echo "安装 agents-cli 工具..."
  pip install --upgrade google-agents-cli
fi

export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
export HOME_INVENTORY_BUCKET="$BUCKET_NAME"

agents-cli deploy --agent-name home_inventory_agent --region "${REGION}"

# Extract Reasoning Engine resource name
RE_NAME=$(gcloud ai reasoning-engines list --region="${REGION}" --format="value(name)" --sort-by="~createTime" --limit=1)
if [ -z "$RE_NAME" ]; then
  echo -e "${RED}[ERROR] 未找到已部署的 Reasoning Engine 资源！${NC}"
  exit 1
fi
echo -e "${GREEN}✓ 部署成功！Agent Engine Resource:${NC} ${RE_NAME}"

# 6. Deploy Custom Frontend to Cloud Run
echo -e "\n${YELLOW}▶ [6/6] 正在构建并部署前端与反向代理至 Google Cloud Run...${NC}"
gcloud run deploy home-inventory-frontend \
  --source frontend \
  --region "${REGION}" \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="${RE_NAME}",AGENT_DIRECTORY="app",GOOGLE_CLOUD_PROJECT="${PROJECT_ID}",HOME_INVENTORY_BUCKET="${BUCKET_NAME}"

RUN_URL=$(gcloud run services describe home-inventory-frontend --region="${REGION}" --format="value(status.url)")

echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${GREEN}🎉 恭喜！智能管家已全部成功部署到您的个人 GCP 项目！${NC}"
echo -e "${GREEN}🌐 线上服务访问直达链接:${NC} ${RUN_URL}"
echo -e "${GREEN}🇨🇳 中文入口:${NC} ${RUN_URL}"
echo -e "${GREEN}🇯🇵 日本語入口:${NC} ${RUN_URL}/?lang=ja"
echo -e "${GREEN}🇺🇸 English 入口:${NC} ${RUN_URL}/?lang=en"
echo -e "${BLUE}======================================================================${NC}"
