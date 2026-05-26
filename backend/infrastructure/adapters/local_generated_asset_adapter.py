"""Local generated asset adapter."""

from pathlib import Path

from backend.providers.dtos import AssetReferenceDTO


class LocalGeneratedAssetAdapter:
    """Resolve and save generated assets using the current filesystem layout."""

    def __init__(
        self,
        data_dir: str = "data",
        outputs_dir: str = "outputs",
    ) -> None:
        self.projects_dir = Path(data_dir) / "projects"
        self.outputs_dir = Path(outputs_dir)

    def save_project_report(
        self, project_id: str, filename: str, content: str
    ) -> AssetReferenceDTO:
        report_dir = self.projects_dir / project_id / "outputs" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / filename
        report_path.write_text(content, encoding="utf-8")
        return AssetReferenceDTO(path=report_path, media_type="text/markdown")

    def resolve_project_report(self, project_id: str) -> AssetReferenceDTO | None:
        report_dir = self.projects_dir / project_id / "outputs" / "reports"
        return self._first_existing(report_dir.glob("report_*.md"), media_type="text/markdown")

    @staticmethod
    def _first_existing(paths, media_type: str) -> AssetReferenceDTO | None:
        for path in sorted(paths):
            if path.exists():
                return AssetReferenceDTO(path=path, media_type=media_type)
        return None
