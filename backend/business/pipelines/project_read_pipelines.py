"""Project-level read pipelines: customers and per-item recommendation."""

from __future__ import annotations

from typing import Any

from backend.abilities.recommendation.recommend_for_item import recommend_for_item
from backend.core.errors import InfrastructureError, NotFoundError
from backend.models.project import Project
from backend.providers.container import ProvidersContainer

CUSTOMER_FIELD_MAP: dict[str, str] = {
    "id": "客户ID",
    "name": "客户细分",
    "recency": "R_最近购买天数",
    "frequency": "F_购买频次",
    "monetary": "M_消费金额",
    "cluster_id": "客户分群",
}


class ProjectCustomerPipeline:
    """List normalized customer records for a project."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def list(self, project_id: str, cluster_id: int | None = None) -> list[dict[str, Any]]:
        project = self._require_project(project_id)
        rows = self._read_storage_rows(project_id)
        if not rows:
            rows = self._fallback_cluster_rows(project)
        customers = [self._normalize_row(row) for row in rows]
        if cluster_id is not None:
            customers = [c for c in customers if c.get("cluster_id") == cluster_id]
        return customers

    def _require_project(self, project_id: str) -> Project:
        project = self.providers.repository.get_project(project_id)
        if project is None:
            raise NotFoundError(f"项目不存在: {project_id}")
        return project

    def _read_storage_rows(self, project_id: str) -> list[dict[str, Any]]:
        try:
            return self.providers.storage.read_customers(project_id) or []
        except Exception as exc:
            raise InfrastructureError(f"读取客户数据失败: {exc}") from exc

    @staticmethod
    def _fallback_cluster_rows(project: Project) -> list[dict[str, Any]]:
        if project.results is None:
            return []
        clustering_data = project.results.clustering_data or {}
        return list(clustering_data.get("cluster_customers", []) or [])

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for target_key, csv_key in CUSTOMER_FIELD_MAP.items():
            if target_key in row:
                normalized[target_key] = row[target_key]
            elif csv_key in row:
                normalized[target_key] = row[csv_key]
            else:
                normalized[target_key] = None
        normalized["id"] = ProjectCustomerPipeline._coerce_str(normalized.get("id"))
        name = ProjectCustomerPipeline._coerce_str(normalized.get("name"))
        normalized["name"] = name if name is not None else normalized["id"]
        normalized["recency"] = ProjectCustomerPipeline._coerce_int(normalized.get("recency"))
        normalized["frequency"] = ProjectCustomerPipeline._coerce_int(normalized.get("frequency"))
        normalized["monetary"] = ProjectCustomerPipeline._coerce_float(normalized.get("monetary"))
        normalized["cluster_id"] = ProjectCustomerPipeline._coerce_int(normalized.get("cluster_id"))
        return normalized

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_str(value: Any) -> str | None:
        if value is None or value == "":
            return None
        return str(value)


class ProjectRecommendationPipeline:
    """Per-project item recommendation using project dataset and rules."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def recommend_for_item(self, project_id: str, item: str) -> dict[str, Any]:
        project = self.providers.repository.get_project(project_id)
        if project is None:
            raise NotFoundError(f"项目不存在: {project_id}")

        dataset_ref = self.providers.storage.resolve_dataset(project_id)
        if dataset_ref is None:
            raise NotFoundError(f"项目数据集不存在: {project_id}")

        try:
            rules_df = self.providers.association_rules.load_rules(
                project_id=project_id, dataset_path=dataset_ref.path
            )
        except Exception as exc:
            raise InfrastructureError(f"加载关联规则失败: {exc}") from exc

        model_data: dict[str, Any] = {"rules_single": rules_df, "subcategories": []}
        return recommend_for_item(model_data=model_data, item_name=item, dataset=None)
