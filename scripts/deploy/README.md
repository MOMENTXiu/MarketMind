# MarketMind 两机器部署指南

> 适用场景：学校实训环境 / 内网环境 / 无域名 / 无公网 IP
>
> 部署架构：01 前端（Nginx） + 02 后端+Infra（FastAPI + PostgreSQL + Redis + MinIO）

---

## 目录

- [前置条件](#前置条件)
- [机器分工](#机器分工)
- [快速部署](#快速部署)
- [详细步骤](#详细步骤)
- [运维命令](#运维命令)
- [故障排查](#故障排查)

---

## 前置条件

| 要求 | 说明 |
|------|------|
| 两台 Linux 机器 | Ubuntu 22.04+ 或 Debian 12+ 推荐 |
| 内网互通 | 两台机器能在内网互相访问（ping 通） |
| root 权限 | 部署脚本需要 sudo |
| 项目代码 | 已通过 `git clone` 或 `scp` 放到两台机器的 `/opt/marketmind/` |
| 联网 | 安装 Docker、uv、npm 等需要联网 |

---

## 机器分工

```
┌─────────────────────────────────────┐         ┌──────────────────────────────────────────┐
│          01 - 前端机器               │         │            02 - 后端+Infra 机器           │
│         （内网 IP: 192.168.x.10）    │         │         （内网 IP: 192.168.x.20）        │
│                                     │         │                                          │
│  ┌─────────────────────────────┐   │         │  ┌─────────────────────────────────────┐  │
│  │ Nginx                       │   │         │ │ Docker Compose:                     │  │
│  │ • serve frontend/dist/      │   │         │ │   • PostgreSQL 16 (127.0.0.1:5432)  │  │
│  │ • /api → proxy 02:8000      │◄──┼──────┐  │ │   • Redis 7       (127.0.0.1:6379)  │  │
│  │ • /outputs → proxy 02:8000  │   │      │  │ │   • MinIO         (127.0.0.1:9000)  │  │
│  └─────────────────────────────┘   │      │  │ └─────────────────────────────────────┘  │
│                                     │      │  │                                          │
│  开放端口: 80 (HTTP)                │      └──┼─►│ systemd:                            │  │
│                                     │         │ │   • marketmind-api (Uvicorn ×4)     │  │
└─────────────────────────────────────┘         │ │   • marketmind-worker@1/2 (RQ)      │  │
                                                │ └─────────────────────────────────────┘  │
                                                │                                          │
                                                │  开放端口: 8000（仅接受 01 的 IP）        │
                                                └──────────────────────────────────────────┘
```

---

## 快速部署

### 机器 02（后端 + Infra）

```bash
# 1. 上传代码（如未上传）
scp -r ./MarketMind_DevOps_Gitbase root@192.168.x.20:/opt/marketmind

# 2. 在 02 上执行部署脚本
ssh root@192.168.x.20
cd /opt/marketmind
sudo ./scripts/deploy/install-backend.sh

# 脚本会交互式询问：
#   - 前端机器 IP（01）
#   - 本机 IP（02）
#   - 数据库密码（可回车自动生成）
#   - MinIO 密码（可回车自动生成）
#   - JWT Secret（可回车自动生成）
#   - Worker 数量（默认 2）
```

### 机器 01（前端）

```bash
# 1. 上传代码（如未上传）
scp -r ./MarketMind_DevOps_Gitbase root@192.168.x.10:/opt/marketmind

# 2. 在 01 上执行部署脚本
ssh root@192.168.x.10
cd /opt/marketmind
sudo ./scripts/deploy/install-frontend.sh

# 脚本会交互式询问：
#   - 后端机器 IP（02）
#   - 本机 IP（01）
#   - 前端 dist/ 来源（自动检测或现场构建）
```

### 部署完成

```bash
# 从任意机器访问
 curl http://192.168.x.10/           # 前端页面
 curl http://192.168.x.10/api/health/ # 通过 Nginx 代理的健康检查
 curl http://192.168.x.20:8000/api/health/ # 直接访问后端
```

---

## 详细步骤

### 一、准备代码

在两台机器上都执行：

```bash
# 方式 A: git clone
git clone <你的仓库地址> /opt/marketmind

# 方式 B: scp 上传（从开发机）
rsync -avz --exclude node_modules --exclude .venv \
  ./MarketMind_DevOps_Gitbase/ root@目标IP:/opt/marketmind/
```

### 二、机器 02 部署详情

#### 1. 运行安装脚本

```bash
cd /opt/marketmind
sudo ./scripts/deploy/install-backend.sh
```

#### 2. 脚本自动完成的工作

| 步骤 | 说明 |
|------|------|
| 检查依赖 | Docker、docker compose、Python 3.13+、uv |
| 创建用户 | `marketmind`（无登录权限的运行用户） |
| 安装依赖 | `uv sync` 安装 Python 包 |
| 生成配置 | 从模板创建 `.env.production`（密码自动随机生成） |
| 启动基础设施 | Docker Compose 启动 PG + Redis + MinIO |
| 数据库迁移 | `alembic upgrade head` |
| 日志轮转 | 配置 `logrotate` |
| 安装服务 | `systemd` 托管 API + Worker |
| 防火墙 | `ufw` 限制 8000 仅前端 IP 可访问 |

#### 3. 生成的关键文件

```
/opt/marketmind/
├── .env.production              # 生产环境变量（权限 600）
├── outputs/                     # 生成文件目录
├── logs/                        # 应用日志
├── analysis/                    # 数据集目录
└── scripts/deploy/
    ├── docker-compose.infra.yml # 基础设施编排
    ├── env/.env.production      # 环境变量模板
    └── systemd/
        ├── marketmind-api.service
        └── marketmind-worker@.service
```

### 三、机器 01 部署详情

#### 1. 运行安装脚本

```bash
cd /opt/marketmind
sudo ./scripts/deploy/install-frontend.sh
```

#### 2. 前端构建

脚本会自动检测 `frontend/dist/`：

- **已有 dist/**：直接使用
- **有源码无 dist/**：自动运行 `npm ci && npm run build`
- **都没有**：提示手动处理

建议提前在开发机构建好：

```bash
# 在开发机
cd frontend
npm ci
npm run build
# 然后上传 dist/ 到 01
rsync -avz dist/ root@192.168.x.10:/opt/marketmind/frontend/dist/
```

#### 3. Nginx 配置

脚本自动配置并启用：

```
/etc/nginx/sites-available/marketmind  →  /etc/nginx/sites-enabled/marketmind
```

配置内容：
- `listen 80 default_server`（无域名）
- `/` → 前端静态文件（Vue SPA，支持 history 路由）
- `/api/` → 反向代理到 02:8000
- `/outputs/` → 反向代理到 02:8000
- SSE 长连接支持
- Gzip 压缩 + 安全响应头

---

## 运维命令

### 机器 02（后端）

```bash
# 查看服务状态
sudo systemctl status marketmind-api
sudo systemctl status marketmind-worker@1
sudo systemctl status marketmind-worker@2

# 查看日志（实时）
sudo journalctl -u marketmind-api -f
sudo journalctl -u marketmind-worker@1 -f

# 重启服务
sudo systemctl restart marketmind-api
sudo systemctl restart marketmind-worker@{1,2}

# 查看基础设施
sudo docker compose -f /opt/marketmind/scripts/deploy/docker-compose.infra.yml ps
sudo docker compose -f /opt/marketmind/scripts/deploy/docker-compose.infra.yml logs -f

# 数据库
sudo docker exec -it marketmind-postgres psql -U marketmind -d marketmind

# Redis
sudo docker exec -it marketmind-redis redis-cli

# 健康检查
curl http://localhost:8000/api/health/

# Makefile 快捷命令（在项目根目录）
make infra-up-prod      # 启动基础设施
make infra-down-prod    # 停止基础设施
make db-migrate-prod    # 数据库迁移
make status-prod        # 查看所有服务状态
make health             # 健康检查
```

### 机器 01（前端）

```bash
# Nginx
sudo systemctl status nginx
sudo nginx -t                    # 测试配置
sudo systemctl reload nginx      # 重载配置

# 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# 测试
curl -I http://localhost/
curl http://localhost/api/health/
```

---

## 故障排查

### 后端 API 无法启动

```bash
# 1. 检查日志
sudo journalctl -u marketmind-api -n 50 --no-pager

# 2. 检查环境变量
sudo cat /opt/marketmind/.env.production | grep DATABASE_URL

# 3. 检查数据库是否就绪
sudo docker exec marketmind-postgres pg_isready -U marketmind

# 4. 手动测试启动
cd /opt/marketmind
sudo -u marketmind uv run python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Worker 不消费任务

```bash
# 检查 Worker 日志
sudo journalctl -u marketmind-worker@1 -n 50 --no-pager

# 检查 Redis 连接
sudo docker exec marketmind-redis redis-cli ping

# 查看队列中的任务
sudo docker exec marketmind-redis redis-cli lrange rq:queue:retail-analysis 0 -1
```

### 前端访问 502 Bad Gateway

```bash
# 1. 检查 Nginx 错误日志
sudo tail -n 20 /var/log/nginx/error.log

# 2. 确认后端可访问
curl http://后端IP:8000/api/health/

# 3. 检查防火墙
sudo ufw status | grep 8000
```

### 前端路由刷新 404

这是 Vue SPA 的常见问题。Nginx 配置中已处理：

```nginx
try_files $uri $uri/ /index.html;
```

如果仍出现 404，检查 Nginx 配置：

```bash
cat /etc/nginx/sites-enabled/marketmind | grep try_files
```

---

## 配置文件清单

| 文件 | 用途 | 位置 |
|------|------|------|
| `install-backend.sh` | 后端一键安装 | `scripts/deploy/` |
| `install-frontend.sh` | 前端一键安装 | `scripts/deploy/` |
| `docker-compose.infra.yml` | 基础设施编排 | `scripts/deploy/` |
| `.env.production` | 生产环境变量 | 项目根目录（运行时生成） |
| `marketmind-api.service` | API systemd 服务 | `scripts/deploy/systemd/` |
| `marketmind-worker@.service` | Worker systemd 模板 | `scripts/deploy/systemd/` |
| `marketmind-ip.conf` | Nginx 无域名配置 | `scripts/deploy/nginx/` |

---

## 安全注意事项

1. **`.env.production` 权限**：脚本自动设为 `600`，不要手动改成 `644`
2. **JWT Secret**：部署时自动生成随机值，不要硬编码弱密码
3. **数据库密码**：脚本自动生成 32 位随机 hex，记录好备用
4. **防火墙**：8000 端口仅允许前端机器 IP，5432/6379/9000 仅绑定 127.0.0.1
5. **outputs 文件**：当前使用 `local` 模式，文件存在 02 机器本地。如需多后端扩展，切换到 `minio` 模式
