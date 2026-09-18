#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/opt/ai-bole"
SERVICE_USER="ai-bole"
REPO_URL="${AI_BOLE_REPO_URL:-https://github.com/kuangyutong74-hash/AI-.git}"
BRANCH="${AI_BOLE_DEPLOY_BRANCH:-master}"
SOURCE_ARCHIVE="${AI_BOLE_SOURCE_ARCHIVE:-}"
PUBLIC_ORIGIN="${ECS_PUBLIC_ORIGIN:-}"
STAMP="$(date +%Y%m%d-%H%M%S)"
STAGING_DIR="/opt/ai-bole-staging-${STAMP}"
BACKUP_DIR="/opt/ai-bole-rollback-${STAMP}"
SERVICES=(ai-bole-core ai-bole-report ai-bole-chat ai-bole-story ai-bole-deep-sea ai-bole-career ai-bole-portal)

if [[ "${EUID}" -ne 0 ]]; then
  echo "请使用 root 运行此脚本。" >&2
  exit 1
fi
if [[ ! -d "${APP_DIR}" || ! -f "${APP_DIR}/.env" ]]; then
  echo "未找到现有部署或 .env：${APP_DIR}" >&2
  exit 1
fi
if [[ ! "${PUBLIC_ORIGIN}" =~ ^https?://[^/]+$ ]]; then
  echo "请设置 ECS_PUBLIC_ORIGIN，例如 http://47.93.156.176" >&2
  exit 1
fi

cleanup() {
  if [[ -d "${STAGING_DIR}" ]]; then
    rm -rf -- "${STAGING_DIR}"
  fi
}
trap cleanup EXIT

copy_if_present() {
  local relative_path="$1"
  if [[ -e "${APP_DIR}/${relative_path}" ]]; then
    rm -rf -- "${STAGING_DIR:?}/${relative_path}"
    mkdir -p "${STAGING_DIR}/$(dirname "${relative_path}")"
    cp -a "${APP_DIR}/${relative_path}" "${STAGING_DIR}/${relative_path}"
  fi
}

echo "[1/7] 获取部署源码"
if [[ -n "${SOURCE_ARCHIVE}" ]]; then
  if [[ ! -f "${SOURCE_ARCHIVE}" ]]; then
    echo "找不到部署归档：${SOURCE_ARCHIVE}" >&2
    exit 1
  fi
  mkdir -p "${STAGING_DIR}"
  tar -xzf "${SOURCE_ARCHIVE}" -C "${STAGING_DIR}"
  DEPLOY_VERSION="${AI_BOLE_DEPLOY_VERSION:-本地归档-${STAMP}}"
else
  git -c http.version=HTTP/1.1 clone --depth 1 --branch "${BRANCH}" "${REPO_URL}" "${STAGING_DIR}"
  DEPLOY_VERSION="$(git -C "${STAGING_DIR}" rev-parse --short HEAD)"
fi

echo "[2/7] 保留密钥与业务数据"
cp -a "${APP_DIR}/.env" "${STAGING_DIR}/.env"
copy_if_present "modules/platform-core/data"
copy_if_present "modules/chat/data"
copy_if_present "modules/story/story_cocreate.db"
copy_if_present "modules/career/backend/career_sim.db"

echo "[3/7] 应用 ECS 公网地址"
(cd "${STAGING_DIR}" && ECS_PUBLIC_ORIGIN="${PUBLIC_ORIGIN}" node scripts/apply-ecs-public-origin.mjs)

echo "[4/7] 安装 Node.js 依赖"
for project in \
  "." \
  "modules/chat" \
  "modules/story/frontend" \
  "modules/deep-sea" \
  "modules/talent-report"; do
  (cd "${STAGING_DIR}/${project}" && npm ci --no-audit --no-fund)
done

echo "[5/7] 安装 Python 依赖"
python_projects=(
  "modules/story/backend|requirements.txt"
  "modules/deep-sea|server/requirements.txt"
  "modules/career/backend|requirements.txt"
  "modules/platform-core|requirements.txt"
  "modules/report-agent|requirements.txt"
)
for item in "${python_projects[@]}"; do
  project="${item%%|*}"
  requirements="${item#*|}"
  python3 -m venv "${STAGING_DIR}/${project}/.venv"
  "${STAGING_DIR}/${project}/.venv/bin/python" -m pip install --disable-pip-version-check -r "${STAGING_DIR}/${project}/${requirements}"
done

echo "[6/7] 构建前端"
(cd "${STAGING_DIR}" && npm run build)
(cd "${STAGING_DIR}/modules/story/frontend" && npm run build)
(cd "${STAGING_DIR}/modules/deep-sea" && npm run build)
(cd "${STAGING_DIR}/modules/talent-report" && npm run build)
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${STAGING_DIR}"

echo "[7/7] 切换版本并检查服务"
systemctl stop "${SERVICES[@]}"
mv "${APP_DIR}" "${BACKUP_DIR}"
mv "${STAGING_DIR}" "${APP_DIR}"

if systemctl start "${SERVICES[@]}" \
  && sleep 5 \
  && curl --fail --silent --show-error http://127.0.0.1:8120/api/health >/dev/null \
  && curl --fail --silent --show-error http://127.0.0.1:8030/health >/dev/null \
  && curl --fail --silent --show-error http://127.0.0.1:3100/home.html >/dev/null \
  && curl --fail --silent --show-error http://127.0.0.1:8110/api/health >/dev/null \
  && curl --fail --silent --show-error http://127.0.0.1:8105/api/health >/dev/null \
  && curl --fail --silent --show-error http://127.0.0.1:8100/ >/dev/null \
  && curl --fail --silent --show-error http://127.0.0.1:4173/ >/dev/null; then
  rm -rf -- "${BACKUP_DIR}"
  trap - EXIT
  echo "部署成功：${DEPLOY_VERSION}"
  exit 0
fi

echo "健康检查失败，正在回滚。" >&2
systemctl stop "${SERVICES[@]}" || true
mv "${APP_DIR}" "${STAGING_DIR}"
mv "${BACKUP_DIR}" "${APP_DIR}"
systemctl start "${SERVICES[@]}" || true
exit 1
