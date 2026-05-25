"""Local generated asset adapter."""

import shutil
from pathlib import Path

from backend.providers.dtos import AssetReferenceDTO


class LocalGeneratedAssetAdapter:
    """Resolve and save generated assets using the current filesystem layout."""

    def __init__(
        self,
        data_dir: str = "data",
        outputs_dir: str = "outputs",
        ai_audio_dir: str = "backend/data/audio",
        temp_dir: str = "/tmp",
    ) -> None:
        self.projects_dir = Path(data_dir) / "projects"
        self.outputs_dir = Path(outputs_dir)
        self.ai_audio_dir = Path(ai_audio_dir)
        self.temp_dir = Path(temp_dir)

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

    def save_project_audio(
        self,
        project_id: str,
        filename: str,
        source_path: Path,
    ) -> AssetReferenceDTO:
        audio_dir = self.projects_dir / project_id / "outputs" / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / filename
        if source_path.resolve() != audio_path.resolve():
            shutil.copy2(source_path, audio_path)
        return AssetReferenceDTO(path=audio_path, media_type="audio/mpeg")

    def resolve_project_audio(self, project_id: str) -> AssetReferenceDTO | None:
        audio_dir = self.projects_dir / project_id / "outputs" / "audio"
        return self._first_existing(audio_dir.glob("report_*.mp3"), media_type="audio/mpeg")

    def save_public_audio(self, filename: str, source_path: Path) -> AssetReferenceDTO:
        audio_dir = self.outputs_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / filename
        if source_path.resolve() != audio_path.resolve():
            shutil.copy2(source_path, audio_path)
        return AssetReferenceDTO(
            path=audio_path,
            url=f"/outputs/audio/{filename}",
            media_type="audio/mpeg",
        )

    def save_ai_audio(self, filename: str, source_path: Path) -> AssetReferenceDTO:
        self.ai_audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = self.ai_audio_dir / filename
        if source_path.resolve() != audio_path.resolve():
            shutil.copy2(source_path, audio_path)
        return AssetReferenceDTO(
            path=audio_path,
            url=f"/api/ai-voice/audio/{filename}/",
            media_type="audio/mpeg",
        )

    def resolve_ai_audio(self, filename: str) -> AssetReferenceDTO | None:
        temp_path = self.temp_dir / filename
        if temp_path.exists():
            return AssetReferenceDTO(path=temp_path, media_type="audio/mpeg")

        data_path = self.ai_audio_dir / filename
        if data_path.exists():
            return AssetReferenceDTO(path=data_path, media_type="audio/mpeg")

        return None

    @staticmethod
    def _first_existing(paths, media_type: str) -> AssetReferenceDTO | None:
        for path in sorted(paths):
            if path.exists():
                return AssetReferenceDTO(path=path, media_type=media_type)
        return None
