#!/bin/bash
# =============================================================================
# MarketMind 前端部署脚本（机器 01）
# 学校实训环境 · 无域名 · 纯内网 IP
#
# 运行要求：
#   - 以 root 权限执行（sudo 或 root 用户）
#   - 机器 02 已经部署完成
#   - 项目代码已放在当前目录（或 frontend/dist/ 已就绪）
#
# 用法：
#   cd /opt/marketmind
#   sudo ./scripts/deploy/install-frontend.sh
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
echo -e "${CYAN}║      MarketMind 前端部署（机器 01）                           ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检测本机 IP
DETECTED_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '^127\.' | head -n1 || true)

read -rp "后端机器 IP（02）          [必填]: " BACKEND_IP
read -rp "本机 IP（01，用于确认）    [${DETECTED_IP:-未检测}]: " FRONTEND_IP
FRONTEND_IP="${FRONTEND_IP:-$DETECTED_IP}"
read -rp "安装目录                  [/opt/marketmind]: " INSTALL_DIR
INSTALL_DIR="${INSTALL_DIR:-/opt/marketmind}"

if [ -z "$BACKEND_IP" ] || [ -z "$FRONTEND_IP" ]; then
    err "后端 IP 和本机 IP 必须填写"
    exit 1
fi

info "配置确认："
echo "  后端 IP:  $BACKEND_IP"
echo "  本机 IP:  $FRONTEND_IP"
read -rp "确认开始部署？[Y/n]: " CONFIRM
if [[ "${CONFIRM,,}" == "n" ]]; then
    info "已取消"
    exit 0
fi

# ─── 检查 Nginx ───
info "检查 Nginx..."
if ! command -v nginx &>/dev/null; then
    info "Nginx 未安装，正在安装..."
    apt-get update && apt-get install -y nginx
fi

if ! nginx -v &>/dev/null; then
    err "Nginx 安装失败"
    exit 1
fi
ok "Nginx: $(nginx -v 2>&1 | head -n1)"

# ─── 确定项目路径 ───
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../../frontend/package.json" ]; then
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
    info "检测到项目目录: $PROJECT_DIR"
else
    PROJECT_DIR="$INSTALL_DIR"
fi

# 确保安装目录存在
mkdir -p "$INSTALL_DIR"

# ─── 准备前端 dist/ ───
info "准备前端构建产物..."

DIST_SOURCE=""

# 1. 检查当前目录是否已有 dist/
if [ -d "$PROJECT_DIR/frontend/dist" ] && [ "$(ls -A "$PROJECT_DIR/frontend/dist" 2>/dev/null)" ]; then
    DIST_SOURCE="$PROJECT_DIR/frontend/dist"
    ok "找到现有构建产物: $DIST_SOURCE"
else
    warn "未找到 frontend/dist/"

    # 2. 尝试现场构建
    if [ -f "$PROJECT_DIR/frontend/package.json" ] && command -v npm &>/dev/null; then
        info "检测到源码和 npm，尝试现场构建..."
        cd "$PROJECT_DIR/frontend"

        # 确保使用生产环境变量（API base URL 为空，走相对路径）
        if [ ! -f .env.production ]; then
            echo "VITE_API_BASE_URL=" > .env.production
            echo "VITE_API_TIMEOUT=30000" >> .env.production
        fi

        npm ci --prefer-offline --no-audit
        npm run build

        if [ -d "dist" ] && [ "$(ls -A dist 2>/dev/null)" ]; then
            DIST_SOURCE="$PROJECT_DIR/frontend/dist"
            ok "现场构建成功: $DIST_SOURCE"
        else
            err "构建失败，dist/ 目录为空"
            exit 1
        fi
    else
        err ""
        err "无法自动准备前端构建产物。请手动执行以下步骤之一："
        err ""
        err "  方案 A：在开发机构建后上传"
        err "    cd frontend && npm ci && npm run build"
        err "    rsync -avz frontend/dist/ root@${FRONTEND_IP}:${INSTALL_DIR}/frontend/dist/"
        err ""
        err "  方案 B：在机器 01 上安装 Node.js 后构建"
        err "    apt install -y nodejs npm"
        err "    cd ${INSTALL_DIR}/frontend && npm ci && npm run build"
        err ""
        err "  方案 C：从机器 02 拷贝（如果 02 上已构建）"
        err "    scp -r root@${BACKEND_IP}:${INSTALL_DIR}/frontend/dist/ ${INSTALL_DIR}/frontend/"
        err ""
        exit 1
    fi
fi

# 拷贝 dist/ 到安装目录
mkdir -p "$INSTALL_DIR/frontend"
if [ "$DIST_SOURCE" != "$INSTALL_DIR/frontend/dist" ]; then
    rsync -a --delete "$DIST_SOURCE/" "$INSTALL_DIR/frontend/dist/" || cp -r "$DIST_SOURCE"/* "$INSTALL_DIR/frontend/dist/"
fi
ok "前端文件已部署到 $INSTALL_DIR/frontend/dist/"

# ─── 配置 Nginx ───
info "配置 Nginx..."

NGINX_TEMPLATE="$PROJECT_DIR/scripts/deploy/nginx/marketmind-ip.conf"
if [ ! -f "$NGINX_TEMPLATE" ]; then
    err "Nginx 模板不存在: $NGINX_TEMPLATE"
    exit 1
fi

# 替换后端 IP
cp "$NGINX_TEMPLATE" /etc/nginx/sites-available/marketmind
sed -i "s/__BACKEND_IP__/$BACKEND_IP/g" /etc/nginx/sites-available/marketmind

# 启用站点
ln -sf /etc/nginx/sites-available/marketmind /etc/nginx/sites-enabled/

# 删除默认站点（避免冲突）
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm -f /etc/nginx/sites-enabled/default
    ok "已禁用 Nginx 默认站点"
fi

# 测试配置
if nginx -t; then
    ok "Nginx 配置测试通过"
else
    err "Nginx 配置测试失败"
    exit 1
fi

# 重载 Nginx
systemctl restart nginx
systemctl enable nginx
ok "Nginx 已启动并启用开机自启"

# ─── 防火墙配置 ───
info "配置防火墙..."
if command -v ufw &>/dev/null; then
    # 开放 HTTP
    ufw allow 80/tcp comment 'MarketMind HTTP'
    # 确保 SSH 开放
    ufw status | grep -q "22/tcp" || ufw allow 22/tcp comment 'SSH'
    # 启用防火墙
    ufw status numbered | grep -q "Status: active" || echo "y" | ufw enable
    ok "ufw 防火墙已配置（开放 80）"
else
    warn "ufw 未安装，请手动确保 80 端口可访问"
fi

# ─── 验证部署 ───
info "验证前端部署..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1/" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    ok "Nginx 前端服务正常（HTTP 200）"
else
    warn "Nginx 返回 HTTP $HTTP_CODE，请检查配置"
fi

info "验证后端连通性..."
API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "http://$BACKEND_IP:8000/api/health/" 2>/dev/null || echo "000")
if [ "$API_HEALTH" = "200" ]; then
    ok "后端 API 连通正常（HTTP 200）"
else
    warn "后端 API 返回 HTTP $API_HEALTH，请确认机器 02 已部署完成"
fi

# ─── 部署完成 ───
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           MarketMind 前端部署完成！                           ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
ok "机器 01 ($FRONTEND_IP) 已就绪"
echo ""
echo -e "${YELLOW}访问地址：${NC}"
echo "  前端页面:     http://$FRONTEND_IP/"
echo "  后端代理:     http://$FRONTEND_IP/api/"
echo ""
echo -e "${YELLOW}常用命令：${NC}"
echo "  测试 Nginx:   curl -I http://$FRONTEND_IP/"
echo "  测试 API:     curl http://$FRONTEND_IP/api/health/"
echo "  查看日志:     tail -f /var/log/nginx/access.log"
echo "  重载配置:     sudo systemctl reload nginx"
echo ""
echo -e "${YELLOW}从浏览器访问：http://${FRONTEND_IP}/${NC}"
echo ""
