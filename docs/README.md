# 文档地图

## 当前必读

| 文档 | 适用场景 |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 理解当前 Vue 3 + FastAPI runtime、分层架构、双分析链路、存储边界。 |
| [requirements-analysis.md](requirements-analysis.md) | 面向课程/项目材料的需求分析书，汇总背景、范围、功能、非功能、验收和约束。 |
| [project-solution-design.md](project-solution-design.md) | 面向课程/项目材料的方案设计书，汇总总体架构、功能方案、接口、部署、质量保障和风险。 |
| [backend-api.md](backend-api.md) | 前端、脚本、测试或第三方调用后端 HTTP 接口。 |
| [frontend-api-integration-plan.md](frontend-api-integration-plan.md) | 了解前端 API 接入现状、已完成项和后续补强计划。 |
| [QUICKSTART.md](QUICKSTART.md) | 本地启动、运行基础设施、执行质量门。 |
| [USAGE_GUIDE.md](USAGE_GUIDE.md) | 使用 Retail V2 与 Data Processing 前端流程。 |
| [commands.md](commands.md) | 查询 Makefile 命令契约。 |
| [env.md](env.md) | 配置后端、前端、PostgreSQL、Redis 环境变量。 |
| [development.md](development.md) | 开发流程、质量门、Retail worker runtime、commit 前检查。 |

## 架构与迁移记录

| 文档 | 状态 |
| --- | --- |
| [architecture/analysis-v2-integration-design.md](architecture/analysis-v2-integration-design.md) | Retail/Analysis V2 集成设计记录。 |
| [architecture/analysis-v2-integration-checklist.md](architecture/analysis-v2-integration-checklist.md) | Retail/Analysis V2 集成检查清单。 |
| [architecture/data-processing-pipeline-integration-design.md](architecture/data-processing-pipeline-integration-design.md) | Data Processing 链路设计记录。 |
| [architecture/data-processing-pipeline-integration-checklist.md](architecture/data-processing-pipeline-integration-checklist.md) | Data Processing 链路迁移检查清单。 |
| [architecture/construction-checklist.md](architecture/construction-checklist.md) | 架构施工清单与历史验证记录。 |
| [architecture/architecture-change.md](architecture/architecture-change.md) | 架构变更记录。 |
| [architecture/frontend-backend-lack-port-design.md](architecture/frontend-backend-lack-port-design.md) | 前后端接口缺失设计方案。 |
| [architecture/frontend-backend-lack-port-checklist.md](architecture/frontend-backend-lack-port-checklist.md) | 前后端接口缺失施工清单。 |
| [architecture/minio-object-storage-design.md](architecture/minio-object-storage-design.md) | MinIO 对象存储集成设计记录。 |
| [architecture/minio-object-storage-checklist.md](architecture/minio-object-storage-checklist.md) | MinIO 对象存储集成检查清单。 |
| [architecture/project-script-split-design.md](architecture/project-script-split-design.md) | 本地脚本拆分设计（deploy / start 分离）。 |
| [architecture/project-script-split-checklist.md](architecture/project-script-split-checklist.md) | 本地脚本拆分实施检查清单。 |

## 历史与归档

| 文档 | 说明 |
| --- | --- |
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | 当前路线图与下一阶段计划。 |
| [Project_Report.md](Project_Report.md) | 面向汇报的系统说明，已按当前 API 和架构更新。 |
| [requirements/](requirements/) | 课程/需求规格材料，作为产品背景参考。 |
| [archive/](archive/) | 已完成的迁移计划、TTS 废除记录、数据处理调查报告等历史文档。 |

## 代码外归档

`analysis/` 与 `analysis/data-processing-pipeline/` 是离线实验、算法蓝本和迁移源材料归档。后端 runtime 不直接 import 这些目录；新能力应落到 `backend/abilities/`、`backend/business/`、`backend/providers/` 和 `backend/infrastructure/`。
