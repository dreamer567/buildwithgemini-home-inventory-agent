# 📖 个人 GCP 部署手顺书 (Deployment SOP for Gemini & Developers)

> 本文档专为 **Gemini 智能体（Antigravity / Code Assistant）** 或开发者设计。当你向 Gemini 提出 **“帮我把这个项目部署到我的 GCP 项目”** 时，Gemini 可完全根据本文档的清晰手順，自动有序地执行所有部署动作。

---

## 🤖 给 Gemini 的一键指令提示词 (Prompt to give Gemini)

如果你使用的是 Gemini 编程助手（如 Google Antigravity），只需将以下内容直接发给 Gemini：

```text
请参考仓库中的 DEPLOYMENT_GUIDE.md 部署手顺书，帮我将当前项目部署到我的个人 Google Cloud (GCP) 项目中。
目标项目 ID 为：<你的个人 GCP 项目 ID>
目标部署区域为：us-east1 (或 us-central1)
请先检查 gcloud 登录状态，然后执行自动化部署并验证 Cloud Run 线上服务。
```

---

## 📋 部署前置条件 (Prerequisites)

在开始执行部署步骤前，请确认当前环境满足以下条件：

1. **Google Cloud 账号与项目**：
   - 已创建 GCP 项目（已关联结算账号，如免费试用账户）；
   - 记下项目 ID（例如 `my-inventory-project-456789`）。
2. **终端已安装 CLI 工具**：
   - `gcloud` (Google Cloud SDK)
   - `python3` (>= 3.11) 与 `pip`
   - `git`
3. **账号登录与认证凭据**：
   ```bash
   # 登录 GCP 主账号
   gcloud auth login
   # 配置应用程序默认凭据 (ADC)
   gcloud auth application-default login
   # 设置默认操作项目
   gcloud config set project <YOUR_PROJECT_ID>
   ```

---

## 🌟 方案一：一键全自动部署手順 (Recommended)

仓库根目录已封装自动化脚本 `deploy_to_my_gcp.sh`，可全自动处理 API 开启、存储桶配置、数据库初始化、数据导入、Agent 托管与前端发布。

### 执行命令：
```bash
# 给予脚本执行权限
chmod +x deploy_to_my_gcp.sh

# 执行一键部署 (参数 1: 你的项目 ID, 参数 2: 区域，推荐 us-east1)
./deploy_to_my_gcp.sh <YOUR_PROJECT_ID> us-east1
```

### 自动化执行流水线包含：
1. `gcloud services enable`：开启 6 项必需的 Google Cloud API。
2. `gcloud storage buckets create`：创建多模态资源公开存储桶 `home-inventory-media-<PROJECT_ID>`。
3. `gcloud firestore databases create`：初始化 Native 模式数据库 `(default)`。
4. `seed_firestore.py`：自动写入 3LDK 全屋物品与食材预设数据。
5. `agents-cli deploy`：打包部署 Agent 至 Vertex AI Agent Engine。
6. `gcloud run deploy`：构建并发布 FastAPI + A2UI 前端至 Cloud Run。

脚本运行结束后，将直接输出最终的 **Cloud Run 生产上线 URL**。

---

## 🛠️ 方案二：分步部署详细手順 (Step-by-Step SOP)

如需逐步核验或由 Gemini 分段执行，请遵循以下标准手順：

### 步骤 1：激活必需的 Google Cloud API
```bash
export PROJECT_ID="<YOUR_PROJECT_ID>"
export REGION="us-east1"
gcloud config set project "$PROJECT_ID"

gcloud services enable \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  run.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

### 步骤 2：创建公网多模态媒体存储桶 (GCS Bucket)
用于存放 Gemini 3.1 Flash-Lite 生图与 Omni 短视频：
```bash
export BUCKET_NAME="home-inventory-media-${PROJECT_ID}"

# 创建存储桶
gcloud storage buckets create "gs://${BUCKET_NAME}" --location="${REGION}"

# 配置浏览器公网匿名只读权限 (用于卡片内直接加载图片与视频)
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="allUsers" \
  --role="roles/storage.objectViewer"
```

### 步骤 3：初始化 Cloud Firestore 并灌入初始数据
```bash
# 1. 检查或创建 (default) 原生模式数据库
if ! gcloud firestore databases list --format="value(name)" 2>/dev/null | grep -q "(default)"; then
  gcloud firestore databases create --location="${REGION}" --type=firestore-native
fi

# 2. 安装必要 Python 依赖并灌入初始 3LDK 资产清单
pip install google-cloud-firestore
GOOGLE_CLOUD_PROJECT="${PROJECT_ID}" python3 scripts/seed_firestore.py
```

### 步骤 4：部署 Agent 至 Vertex AI Agent Engine
```bash
# 1. 安装最新版 agents-cli
pip install --upgrade google-agents-cli

# 2. 注入环境变量并执行部署
export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"
export HOME_INVENTORY_BUCKET="${BUCKET_NAME}"

agents-cli deploy --agent-name home_inventory_agent --region "${REGION}"

# 3. 部署成功后获取 Reasoning Engine Resource ID
export RE_NAME=$(gcloud ai reasoning-engines list --region="${REGION}" --format="value(name)" --sort-by="~createTime" --limit=1)
echo "Agent Engine 部署成功: ${RE_NAME}"
```

### 步骤 5：构建并部署定制前端至 Google Cloud Run
```bash
gcloud run deploy home-inventory-frontend \
  --source frontend \
  --region "${REGION}" \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="${RE_NAME}",AGENT_DIRECTORY="app",GOOGLE_CLOUD_PROJECT="${PROJECT_ID}",HOME_INVENTORY_BUCKET="${BUCKET_NAME}"
```

部署完成后，终端将输出专属服务地址：
```text
Service [home-inventory-frontend] revision [home-inventory-frontend-00001] has been deployed and is serving 100 percent of traffic.
Service URL: https://home-inventory-frontend-xxxxxx.us-east1.run.app
```

---

## 🔍 步骤 6：部署后验证与功能验收 (Post-Deploy Verification)

部署完成后，可执行以下命令或点击链接验收功能：

1. **测试前端主页与静态资源加载**：
   ```bash
   RUN_URL=$(gcloud run services describe home-inventory-frontend --region="${REGION}" --format="value(status.url)")
   curl -I "${RUN_URL}"
   ```
   *预期返回：`HTTP/2 200` 或 `HTTP/1.1 200 OK`*

2. **验证三语页面切换**：
   - 🇨🇳 中文入口：`${RUN_URL}`
   - 🇯🇵 日本語入口：`${RUN_URL}/?lang=ja`
   - 🇺🇸 English 入口：`${RUN_URL}/?lang=en`

3. **对话测试（通过浏览器界面或 API 接口）**：
   - **快捷空间查询**：点击左侧 3D 户型图的「LDK 客餐厨」，观察是否正常列出食材、调料与临期进度条。
   - **采购清单生成**：点击「检查库存并生成家庭采购清单」，验证是否返回紧急采购与常备备货卡片。
   - **自然语言寻物**：提问「家里的剪刀放在哪里了？」，验证是否返回玄关与书房的具体存放位置卡片（无任何原始 JSON 泄露）。

---

## ⚠️ 常见避坑排查与关键配置 (Troubleshooting & FAQs)

### 1. `agents-cli deploy` 报 8MB 限制错误 (Request payload exceeds limit)
- **原因**：Agent Platform 接口限制上传包小于 8MB。
- **解决**：仓库根目录下已内置 `.gcloudignore`，自动排除了 `frontend/`、`assets/`、`.webm`、`.mp4` 与测试文件。请确保在仓库根目录执行部署命令，且不要删除 `.gcloudignore`。

### 2. Firestore 报错 "Database (default) does not exist"
- **原因**：新创建的 GCP 项目尚未启用 Firestore 或未初始化数据库。
- **解决**：运行 `gcloud firestore databases create --location=us-east1 --type=firestore-native`。确保类型选择为 **Native 模式（原生模式）**，而非 Datastore 模式。

### 3. 生成的物品照片或视频在网页中无法显示
- **原因**：GCS 存储桶未对公网开放读取权限。
- **解决**：执行以下命令授予匿名只读权限：
  ```bash
  gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="allUsers" \
    --role="roles/storage.objectViewer"
  ```

### 4. 区域 (Region) 推荐
- 推荐使用 `us-east1` 或 `us-central1`。这两个区域全面支持 Vertex AI Reasoning Engine、Gemini 3.6 Flash、Lyria 音频模型以及 Cloud Run，资源充足，配额稳定。
