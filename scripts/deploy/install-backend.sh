#!/bin/bash
# =============================================================================
# MarketMind 后端+Infra 部署脚本（机器 02）
# 学校实训环境 · 无域名 · 纯内网 IP
#
# 运行要求：
#   - 以 root 权限执行（sudo 或 root 用户）
#   - 目标机器已联网（安装 Docker、uv 等）
#   - 项目代码已放在 /opt/marketmind/（git clone 或 scp）
#
# 用法：
#   cd /opt/marketmind
#   sudo ./scripts/deploy/install-backend.sh
# =============================================================================

set -e

# ─── 颜色输出 ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERR]${NC} $*" >&2; }

# ─── 检查 root ───
if [ "$EUID" -ne 0 ]; then
    err "请以 root 权限运行：sudo $0"
    exit 1
fi

# ─── 交互式配置 ───
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║    MarketMind 后端+Infra 部署（机器 02）                      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检测本机 IP（取第一个非 lo 的内网 IP）
DETECTED_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '^127\.' | head -n1 || true)

read -rp "前端机器 IP（01）         [必填]: " FRONTEND_IP
read -rp "本机 IP（02，用于确认）   [${DETECTED_IP:-未检测}]: " BACKEND_IP
BACKEND_IP="${BACKEND_IP:-$DETECTED_IP}"
read -rp "数据库密码（自动生成按回车）: " DB_PASSWORD
read -rp "MinIO 密码（自动生成按回车）: " MINIO_PASSWORD
read -rp "JWT Secret（自动生成按回车）: " JWT_SECRET
read -rp "RQ Worker 数量            [2]: " WORKER_COUNT
read -rp "安装目录                  [/opt/marketmind]: " INSTALL_DIR

# 默认值
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -hex 16)}"
MINIO_PASSWORD="${MINIO_PASSWORD:-$(openssl rand -hex 16)}"
JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}"
WORKER_COUNT="${WORKER_COUNT:-2}"
INSTALL_DIR="${INSTALL_DIR:-/opt/marketmind}"

if [ -z "$FRONTEND_IP" ] || [ -z "$BACKEND_IP" ]; then
    err "前端 IP 和本机 IP 必须填写"
    exit 1
fi

info "配置确认："
echo "  前端 IP:      $FRONTEND_IP"
echo "  本机 IP:      $BACKEND_IP"
echo "  Worker 数量:  $WORKER_COUNT"
echo "  安装目录:     $INSTALL_DIR"
read -rp "确认开始部署？[Y/n]: " CONFIRM
if [[ "${CONFIRM,,}" == "n" ]]; then
    info "已取消"
    exit 0
fi

# ─── 检查依赖 ───
info "检查系统依赖..."

missing_deps=()

if ! command -v docker &>/dev/null; then
    missing_deps+=("docker")
fi
if ! docker compose version &>/dev/null 2>&1; then
    missing_deps+=("docker-compose-plugin")
fi
if ! command -v python3 &>/dev/null; then
    missing_deps+=("python3")
fi
PYTHON_VER=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' || true)
if [[ "${PYTHON_VER%%.*}" -lt 3 ]] || [[ "${PYTHON_VER#*.}" -lt 13 ]]; then
    warn "Python 版本 $PYTHON_VER，建议升级到 3.13+"
fi
if ! command -v curl &>/dev/null; then
    missing_deps+=("curl")
fi

if [ ${#missing_deps[@]} -gt 0 ]; then
    err "缺少依赖: ${missing_deps[*]}"
    info "请先安装："
    echo "  apt update && apt install -y docker.io docker-compose-plugin python3 python3-pip curl"
    exit 1
fi
ok "系统依赖检查通过"

# ─── 安装 / 确认 uv ───
info "检查 uv..."
if ! command -v uv &>/dev/null; then
    warn "uv 未安装，正在安装..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
UV_BIN=$(command -v uv)
ok "uv: $UV_BIN"

# 将 uv 链接到 /usr/local/bin，确保 systemd 能找到
if [ ! -f /usr/local/bin/uv ]; then
    ln -sf "$UV_BIN" /usr/local/bin/uv
    ok "uv 已链接到 /usr/local/bin/uv"
fi

# ─── 创建用户和目录 ───
info "创建运行用户 marketmind..."
if ! id -u marketmind &>/dev/null; then
    useradd -r -s /bin/false -d /opt/marketmind -m marketmind
    ok "用户 marketmind 已创建"
else
    ok "用户 marketmind 已存在"
fi

mkdir -p "$INSTALL_DIR" /var/log/marketmind
chown -R marketmind:marketmind "$INSTALL_DIR" /var/log/marketmind
chmod 755 /var/log/marketmind

# ─── 确定项目路径 ───
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../../pyproject.toml" ]; then
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
    info "检测到项目目录: $PROJECT_DIR"
else
    PROJECT_DIR="$INSTALL_DIR"
    warn "未检测到项目代码，假设代码在 $INSTALL_DIR"
    if [ ! -f "$INSTALL_DIR/pyproject.toml" ]; then
        err "$INSTALL_DIR 下没有项目代码，请先 git clone 或 scp 代码到此目录"
        exit 1
    fi
fi

# 如果项目目录不是安装目录，且安装目录为空，则拷贝
if [ "$PROJECT_DIR" != "$INSTALL_DIR" ]; then
    info "将项目代码同步到 $INSTALL_DIR ..."
    rsync -a --delete "$PROJECT_DIR/" "$INSTALL_DIR/" || cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"
    chown -R marketmind:marketmind "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# ─── 安装 Python 依赖 ───
info "安装 Python 依赖（uv sync）..."
sudo -u marketmind "$UV_BIN" sync
ok "Python 依赖安装完成"

# ─── 生成生产环境变量 ───
info "生成生产环境配置 .env.production ..."

ENV_TEMPLATE="$INSTALL_DIR/scripts/deploy/env/.env.production"
if [ ! -f "$ENV_TEMPLATE" ]; then
    err "模板文件不存在: $ENV_TEMPLATE"
    exit 1
fi

cp "$ENV_TEMPLATE" "$INSTALL_DIR/.env.production"
sed -i "s|__FRONTEND_IP__|$FRONTEND_IP|g" "$INSTALL_DIR/.env.production"
sed -i "s|__DB_PASSWORD__|$DB_PASSWORD|g" "$INSTALL_DIR/.env.production"
sed -i "s|__MINIO_PASSWORD__|$MINIO_PASSWORD|g" "$INSTALL_DIR/.env.production"
sed -i "s|__JWT_SECRET__|$JWT_SECRET|g" "$INSTALL_DIR/.env.production"

chmod 600 "$INSTALL_DIR/.env.production"
chown marketmind:marketmind "$INSTALL_DIR/.env.production"
ok ".env.production 已生成（权限 600）"

# ─── 创建数据目录 ───
mkdir -p "$INSTALL_DIR/outputs/charts" "$INSTALL_DIR/outputs/reports" \
         "$INSTALL_DIR/analysis" "$INSTALL_DIR/logs"
chown -R marketmind:marketmind "$INSTALL_DIR/outputs" "$INSTALL_DIR/analysis" "$INSTALL_DIR/logs"

# ─── 启动 Docker Compose 基础设施 ───
info "启动基础设施（PostgreSQL + Redis + MinIO）..."
docker compose -f "$INSTALL_DIR/scripts/deploy/docker-compose.infra.yml" \
    --env-file "$INSTALL_DIR/.env.production" \
    up -d

# 等待健康检查
wait_for_container() {
    local name=$1
    local max_wait=${2:-60}
    local waited=0
    info "等待 $name 就绪..."
    while [ $waited -lt $max_wait ]; do
        status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "unknown")
        if [ "$status" = "healthy" ]; then
            ok "$name 已就绪"
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
        echo -n "."
    done
    echo ""
    err "$name 未在 ${max_wait}s 内就绪"
    docker compose -f "$INSTALL_DIR/scripts/deploy/docker-compose.infra.yml" logs "$name" | tail -n 20
    exit 1
}

wait_for_container "marketmind-postgres" 60
wait_for_container "marketmind-redis" 30
wait_for_container "marketmind-minio" 30
ok "所有基础设施服务已就绪"

# ─── 数据库迁移 ───
info "执行数据库迁移..."
sudo -u marketmind "$UV_BIN" run alembic upgrade head
ok "数据库迁移完成"

# ─── 安装 logrotate ───
info "配置日志轮转..."
cat > /etc/logrotate.d/marketmind <<'EOF'
/var/log/marketmind/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 marketmind marketmind
    sharedscripts
    postrotate
        systemctl reload marketmind-api >/dev/null 2>&1 || true
    endscript
}
EOF
ok "logrotate 已配置"

# ─── 安装 systemd 服务 ───
info "安装 systemd 服务..."
cp "$INSTALL_DIR/scripts/deploy/systemd/marketmind-api.service" /etc/systemd/system/
cp "$INSTALL_DIR/scripts/deploy/systemd/marketmind-worker@.service" /etc/systemd/system/

# 如果 uv 不在 /usr/local/bin/uv，需要替换 systemd 中的路径
if [ "$UV_BIN" != "/usr/local/bin/uv" ] && [ -f /usr/local/bin/uv ]; then
    : # 已经做了符号链接，不需要替换
fi

systemctl daemon-reload

systemctl enable marketmind-api
systemctl start marketmind-api

for i in $(seq 1 "$WORKER_COUNT"); do
    systemctl enable "marketmind-worker@$i"
    systemctl start "marketmind-worker@$i"
done
ok "systemd 服务已安装并启动"

# ─── 等待后端就绪 ───
info "等待后端 API 就绪..."
for i in {1..30}; do
    if curl -fsS "http://127.0.0.1:8000/api/health/" >/dev/null 2>&1; then
        ok "后端 API 已就绪"
        break
    fi
    sleep 1
    echo -n "."
done

if ! curl -fsS "http://127.0.0.1:8000/api/health/" >/dev/null 2>&1; then
    warn "后端 API 似乎未就绪，请检查日志: journalctl -u marketmind-api -n 50"
fi

# ─── 防火墙配置 ───
info "配置防火墙..."
if command -v ufw &>/dev/null; then
    # 允许前端机器访问 8000
    ufw allow from "$FRONTEND_IP" to any port 8000 proto tcp comment 'MarketMind API'
    # 拒绝其他来源访问 8000
    ufw deny 8000/tcp comment 'Deny external API access'
    # SSH 保持开放（如果还没开的话）
    ufw status | grep -q "22/tcp" || ufw allow 22/tcp comment 'SSH'
    # 启用防火墙（如果还没启用）
    ufw status numbered | grep -q "Status: active" || echo "y" | ufw enable
    ok "ufw 防火墙已配置（仅 $FRONTEND_IP 可访问 8000）"
else
    warn "ufw 未安装，请手动配置防火墙限制 8000 端口访问"
fi

# ─── 部署完成 ───
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         MarketMind 后端+Infra 部署完成！                      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
ok "机器 02 ($BACKEND_IP) 已就绪"
echo ""
echo -e "${YELLOW}访问信息：${NC}"
echo "  API 地址:     http://$BACKEND_IP:8000/api"
echo "  健康检查:     http://$BACKEND_IP:8000/api/health/"
echo "  API 文档:     http://$BACKEND_IP:8000/api/docs"
echo ""
echo -e "${YELLOW}常用命令：${NC}"
echo "  查看 API 日志:    sudo journalctl -u marketmind-api -f"
echo "  查看 Worker 日志: sudo journalctl -u marketmind-worker@1 -f"
echo "  重启 API:         sudo systemctl restart marketmind-api"
echo "  重启 Worker:      sudo systemctl restart marketmind-worker@{1..$WORKER_COUNT}"
echo "  查看服务状态:     sudo systemctl status marketmind-api"
echo ""
echo -e "${YELLOW}基础设施：${NC}"
echo "  PostgreSQL: docker exec -it marketmind-postgres psql -U marketmind -d marketmind"
echo "  Redis:      docker exec -it marketmind-redis redis-cli"
echo "  MinIO:      docker exec -it marketmind-minio mc ls local/"
echo ""
echo -e "${YELLOW}下一步：在机器 01（$FRONTEND_IP）上运行 install-frontend.sh${NC}"
echo ""
