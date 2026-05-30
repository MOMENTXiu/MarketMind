# MarketMind 文档

> 四层目录：
> - `docs/` 根 — **项目介绍**（纵览、路线图、需求）
> - `deploy/` — **部署与运维**（环境变量、API、启动、Admin）
> - `develop/` — **开发设计**（架构变更、施工清单、E2E 分析）
> - `archive/` — **已完成归档**（`deploy/` + `develop/` 子目录）

---

## 项目介绍 (docs/ 根目录)

| 文档 | 说明 |
| --- | --- |
| [../README.md](../README.md) | 项目首页：技术栈、快速启动、当前能力 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统架构：五层架构、双分析链路、存储边界 |
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | 项目路线图 |
| [Project_Report.md](Project_Report.md) | 面向汇报的系统说明 |
| [intro/INTRO_PAGE_BRIEF.md](intro/INTRO_PAGE_BRIEF.md) | `/project-intro` 设计简述 |
| [requirements/software-requirements-specification.md](requirements/software-requirements-specification.md) | 软件需求规格说明 |
| [requirements/user-story.md](requirements/user-story.md) | 用户故事 |

---

## 部署与运维 (deploy/)

面向：部署人员、运维人员、API 接入方。

| 文档 | 说明 |
| --- | --- |
| [deploy/QUICKSTART.md](deploy/QUICKSTART.md) | 本地快速启动 |
| [deploy/env.md](deploy/env.md) | 环境变量参考：Backend / Auth / LLM / Bark / Admin |
| [deploy/commands.md](deploy/commands.md) | Makefile 命令契约 |
| [deploy/development.md](deploy/development.md) | 本地基础设施、质量门禁、Commit 规范 |
| [deploy/USAGE_GUIDE.md](deploy/USAGE_GUIDE.md) | 前端使用指南 |
| [deploy/backend-api.md](deploy/backend-api.md) | 后端 HTTP API 完整契约 |
| [deploy/frontend-api-integration-plan.md](deploy/frontend-api-integration-plan.md) | 前端 API 接入现状 |
| [deploy/frontend-backend-lack-port.md](deploy/frontend-backend-lack-port.md) | 端口冲突排查 |
| [deploy/admin/admin-console-design.md](deploy/admin/admin-console-design.md) | Admin Console 设计、部署、安全模型 |

```bash
./scripts/setup-admin.sh     # 交互式创建管理员
./scripts/deploy-project.sh  # 基础设施 + 依赖 + 迁移
./scripts/start-project.sh   # 启动全部服务
```

---

## 开发设计 (develop/)

面向：开发者、Agent、接手项目的 AI。

| 文档 | 说明 |
| --- | --- |
| [develop/e2e-auth-flow-analysis.md](develop/e2e-auth-flow-analysis.md) | Auth 端到端流程分析 |
| [develop/e2e-auth-flow-fix-checklist.md](develop/e2e-auth-flow-fix-checklist.md) | Auth 修复清单 |
| [develop/admin/admin-settings-edit-design.md](develop/admin/admin-settings-edit-design.md) | Settings 在线编辑架构设计 |
| [develop/admin/admin-ux-audit.md](develop/admin/admin-ux-audit.md) | Admin UX 审查报告 |

### 架构变更记录 (develop/architecture/)

| 文档 | 说明 |
| --- | --- |
| [develop/architecture/architecture-change.md](develop/architecture/architecture-change.md) | 架构变更记录 |
| [develop/architecture/construction-checklist.md](develop/architecture/construction-checklist.md) | 架构施工清单 |
| [develop/architecture/user-system-auth-design.md](develop/architecture/user-system-auth-design.md) | 用户系统设计 |
| [develop/architecture/user-system-auth-checklist.md](develop/architecture/user-system-auth-checklist.md) | 用户系统施工清单 |
| [develop/architecture/minio-object-storage-design.md](develop/architecture/minio-object-storage-design.md) | MinIO 集成设计 |
| [develop/architecture/minio-object-storage-checklist.md](develop/architecture/minio-object-storage-checklist.md) | MinIO 施工清单 |
| [develop/architecture/project-script-split-design.md](develop/architecture/project-script-split-design.md) | 脚本拆分设计 |
| [develop/architecture/project-script-split-checklist.md](develop/architecture/project-script-split-checklist.md) | 脚本拆分实施清单 |

---

## 已完成归档 (archive/)

### archive/deploy/ — 部署类归档

| 文档 | 说明 |
| --- | --- |
| [archive/deploy/admin-console-implementation-checklist.md](archive/deploy/admin-console-implementation-checklist.md) | Admin Console 施工清单 ✅ |
| [archive/deploy/admin-settings-edit-checklist.md](archive/deploy/admin-settings-edit-checklist.md) | Settings 在线编辑施工清单 ✅ |
| [archive/deploy/frontend-backend-lack-port-design.md](archive/deploy/frontend-backend-lack-port-design.md) | 前后端接口缺失设计 |
| [archive/deploy/frontend-backend-lack-port-checklist.md](archive/deploy/frontend-backend-lack-port-checklist.md) | 前后端接口缺失施工清单 |
| [archive/deploy/postgres-redis-docker-migration-plan.md](archive/deploy/postgres-redis-docker-migration-plan.md) | PostgreSQL/Redis 迁移计划 |
| [archive/deploy/data-processing-project-entry-checklist.md](archive/deploy/data-processing-project-entry-checklist.md) | DP 项目入口施工清单 |
| [archive/deploy/data-processing-project-entry-report.md](archive/deploy/data-processing-project-entry-report.md) | DP 项目入口调查报告 |

### archive/develop/ — 开发类归档

| 文档 | 说明 |
| --- | --- |
| [archive/develop/analysis-v2-integration-design.md](archive/develop/analysis-v2-integration-design.md) | Retail V2 集成设计 |
| [archive/develop/analysis-v2-integration-checklist.md](archive/develop/analysis-v2-integration-checklist.md) | Retail V2 施工清单 |
| [archive/develop/data-processing-pipeline-integration-design.md](archive/develop/data-processing-pipeline-integration-design.md) | Data Processing 链路设计 |
| [archive/develop/data-processing-pipeline-integration-checklist.md](archive/develop/data-processing-pipeline-integration-checklist.md) | Data Processing 施工清单 |
| [archive/develop/data-processing-echarts-frontend-design.md](archive/develop/data-processing-echarts-frontend-design.md) | ECharts 前端设计 |
| [archive/develop/data-processing-echarts-frontend-checklist.md](archive/develop/data-processing-echarts-frontend-checklist.md) | ECharts 施工清单 |
| [archive/develop/data-processing-pipeline-review-fix-plan.md](archive/develop/data-processing-pipeline-review-fix-plan.md) | DP 审查修复计划 |
| [archive/develop/abolish-tts-plan.md](archive/develop/abolish-tts-plan.md) | TTS 废除计划 |
| [archive/develop/TTS_VOICE_INVENTORY.md](archive/develop/TTS_VOICE_INVENTORY.md) | TTS 语音库存 |
