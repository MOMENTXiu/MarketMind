# MarketMind 文档

> 分为三个 Part：
> - **Part 1 介绍** — 了解项目是什么、能做什么、系统架构
> - **Part 2 运维** — 部署、配置、启动、API 接入、日常操作
> - **Part 3 开发** — 架构设计、施工清单、变更记录

---

## Part 1 — 项目介绍

入门阅读顺序：根目录 README → ARCHITECTURE → 按需深读。

| 文档 | 说明 |
| --- | --- |
| [../README.md](../README.md) | 项目首页：技术栈、快速启动、当前能力 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统架构：Vue 3 + FastAPI runtime、五层架构、双分析链路、存储边界 |
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | 项目路线图与下一阶段计划 |
| [Project_Report.md](Project_Report.md) | 面向汇报的系统说明 |
| [intro/INTRO_PAGE_BRIEF.md](intro/INTRO_PAGE_BRIEF.md) | 项目介绍页（`/project-intro`）设计简述 |
| [requirements/software-requirements-specification.md](requirements/software-requirements-specification.md) | 软件需求规格说明 |
| [requirements/user-story.md](requirements/user-story.md) | 用户故事 |

---

## Part 2 — 运维文档

面向：部署人员、运维人员、API 接入方。

### 首次部署

| 文档 | 说明 |
| --- | --- |
| [QUICKSTART.md](QUICKSTART.md) | 本地快速启动：依赖安装、基础设施、质量门禁 |
| [env.md](env.md) | 环境变量参考：Backend / Frontend / Auth / LLM / Bark / Admin |
| [commands.md](commands.md) | Makefile 命令契约与参数说明 |

### 日常运维

| 文档 | 说明 |
| --- | --- |
| [USAGE_GUIDE.md](USAGE_GUIDE.md) | 前端使用指南：Retail V2 与 Data Processing 操作流程 |
| [development.md](development.md) | 本地基础设施（Docker）、质量门禁、Commit 规范、Hooks |
| [frontend-backend-lack-port.md](frontend-backend-lack-port.md) | 前后端端口冲突排查 |

### Admin Console

| 文档 | 说明 |
| --- | --- |
| [admin/admin-console-design.md](admin/admin-console-design.md) | Admin Console 设计：模块说明、API 契约、安全模型、部署步骤 |
| [admin/admin-ux-audit.md](admin/admin-ux-audit.md) | Admin Console UX 审查报告：风格一致性问题与修复记录 |

### API 参考

| 文档 | 说明 |
| --- | --- |
| [backend-api.md](backend-api.md) | 后端 HTTP API 完整契约：Retail V2、Data Processing、Auth、Admin Console |
| [frontend-api-integration-plan.md](frontend-api-integration-plan.md) | 前端 API 接入现状与补强计划 |

### 脚本速查

```bash
./scripts/setup-admin.sh     # 交互式创建管理员
./scripts/deploy-project.sh  # 基础设施 + 依赖 + 迁移
./scripts/start-project.sh   # 启动全部服务
```

---

## Part 3 — 开发文档

面向：开发者、Agent、接手项目的 AI。

### Admin Console

| 文档 | 说明 |
| --- | --- |
| [admin/admin-console-design.md](admin/admin-console-design.md) | Admin Console 系统设计 |
| [admin/admin-settings-edit-design.md](admin/admin-settings-edit-design.md) | Settings 在线编辑架构设计 |
| [admin/admin-ux-audit.md](admin/admin-ux-audit.md) | Admin UX 审查与修复 |

### Auth / E2E

| 文档 | 说明 |
| --- | --- |
| [e2e-auth-flow-analysis.md](e2e-auth-flow-analysis.md) | Auth 端到端流程分析 |
| [e2e-auth-flow-fix-checklist.md](e2e-auth-flow-fix-checklist.md) | Auth 修复清单 |

### 架构变更记录

| 文档 | 说明 |
| --- | --- |
| [architecture/architecture-change.md](architecture/architecture-change.md) | 架构变更记录（当前调用链、目标四层、Provider 边界） |
| [architecture/construction-checklist.md](architecture/construction-checklist.md) | 架构施工清单与历史验证结果 |
| [architecture/user-system-auth-design.md](architecture/user-system-auth-design.md) | 用户系统与认证设计 |
| [architecture/user-system-auth-checklist.md](architecture/user-system-auth-checklist.md) | 用户系统与认证施工清单 |
| [architecture/minio-object-storage-design.md](architecture/minio-object-storage-design.md) | MinIO 对象存储集成设计 |
| [architecture/minio-object-storage-checklist.md](architecture/minio-object-storage-checklist.md) | MinIO 对象存储施工清单 |
| [architecture/project-script-split-design.md](architecture/project-script-split-design.md) | 脚本拆分设计（deploy / start / setup-admin） |
| [architecture/project-script-split-checklist.md](architecture/project-script-split-checklist.md) | 脚本拆分实施清单 |

### 已完成归档

| 文档 | 说明 |
| --- | --- |
| [archive/README.md](archive/README.md) | 归档索引 |
| [archive/admin-console-implementation-checklist.md](archive/admin-console-implementation-checklist.md) | Admin Console 施工清单 ✅ |
| [archive/admin-settings-edit-checklist.md](archive/admin-settings-edit-checklist.md) | Settings 在线编辑施工清单 ✅ |
| [archive/analysis-v2-integration-design.md](archive/analysis-v2-integration-design.md) | Retail/Analysis V2 集成设计 |
| [archive/analysis-v2-integration-checklist.md](archive/analysis-v2-integration-checklist.md) | Retail/Analysis V2 施工清单 |
| [archive/data-processing-pipeline-integration-design.md](archive/data-processing-pipeline-integration-design.md) | Data Processing 链路设计 |
| [archive/data-processing-pipeline-integration-checklist.md](archive/data-processing-pipeline-integration-checklist.md) | Data Processing 施工清单 |
| [archive/data-processing-echarts-frontend-design.md](archive/data-processing-echarts-frontend-design.md) | ECharts 前端设计 |
| [archive/data-processing-echarts-frontend-checklist.md](archive/data-processing-echarts-frontend-checklist.md) | ECharts 前端施工清单 |
| [archive/data-processing-project-entry-checklist.md](archive/data-processing-project-entry-checklist.md) | DP 项目入口施工清单 |
| [archive/data-processing-project-entry-report.md](archive/data-processing-project-entry-report.md) | DP 项目入口调查报告 |
| [archive/data-processing-pipeline-review-fix-plan.md](archive/data-processing-pipeline-review-fix-plan.md) | DP 审查修复计划 |
| [archive/frontend-backend-lack-port-design.md](archive/frontend-backend-lack-port-design.md) | 前后端接口缺失设计 |
| [archive/frontend-backend-lack-port-checklist.md](archive/frontend-backend-lack-port-checklist.md) | 前后端接口缺失施工清单 |
| [archive/postgres-redis-docker-migration-plan.md](archive/postgres-redis-docker-migration-plan.md) | PostgreSQL/Redis 迁移计划 |
| [archive/abolish-tts-plan.md](archive/abolish-tts-plan.md) | TTS 废除计划 |
