"""Infrastructure-owned SQLAlchemy model registry."""

from backend.infrastructure.db.models.analysis_result import AnalysisResultRecord
from backend.infrastructure.db.models.artifact import ArtifactRecord
from backend.infrastructure.db.models.dataset import DatasetRecord
from backend.infrastructure.db.models.processing_run import ProcessingRunRecord
from backend.infrastructure.db.models.project import ProjectRecord
from backend.infrastructure.db.models.sse_ticket import SseTicketRecord
from backend.infrastructure.db.models.uploaded_file import UploadedFileRecord
from backend.infrastructure.db.models.user import UserRecord

__all__ = [
    "AnalysisResultRecord",
    "ArtifactRecord",
    "DatasetRecord",
    "ProcessingRunRecord",
    "ProjectRecord",
    "SseTicketRecord",
    "UploadedFileRecord",
    "UserRecord",
]
