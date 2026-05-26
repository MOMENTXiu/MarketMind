"""
项目存储管理器 - 使用JSON文件存储
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from backend.models.project import Project


class ProjectStorage:
    """项目存储管理器"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.projects_file = self.data_dir / "projects.json"
        self.projects_dir = self.data_dir / "projects"

        # 初始化目录结构
        self.data_dir.mkdir(exist_ok=True)
        self.projects_dir.mkdir(exist_ok=True)

        # 初始化项目文件
        if not self.projects_file.exists():
            self._save_projects([])

    def _load_projects(self) -> List[Project]:
        """加载所有项目"""
        try:
            with open(self.projects_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [Project(**item) for item in data]
        except Exception as e:
            print(f"加载项目失败: {e}")
            return []

    def _save_projects(self, projects: List[Project]):
        """保存所有项目"""
        with open(self.projects_file, "w", encoding="utf-8") as f:
            data = [p.model_dump(mode="json") for p in projects]
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def create_project(self, project: Project) -> Project:
        """创建新项目"""
        projects = self._load_projects()
        projects.append(project)
        self._save_projects(projects)

        # 创建项目目录
        project_dir = self.projects_dir / project.id
        project_dir.mkdir(exist_ok=True)
        (project_dir / "outputs").mkdir(exist_ok=True)
        (project_dir / "outputs" / "charts").mkdir(exist_ok=True)
        (project_dir / "outputs" / "reports").mkdir(exist_ok=True)

        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """获取单个项目"""
        projects = self._load_projects()
        for project in projects:
            if project.id == project_id:
                return project
        return None

    def list_projects(self, skip: int = 0, limit: int = 100) -> List[Project]:
        """获取项目列表"""
        projects = self._load_projects()
        # 按创建时间倒序排列
        projects.sort(key=lambda x: x.created_at, reverse=True)
        return projects[skip : skip + limit]

    def update_project(self, project_id: str, updates: dict) -> Optional[Project]:
        """更新项目"""
        projects = self._load_projects()
        for i, project in enumerate(projects):
            if project.id == project_id:
                # 更新字段
                for key, value in updates.items():
                    if value is not None and hasattr(project, key):
                        setattr(project, key, value)
                project.updated_at = datetime.now()
                projects[i] = project
                self._save_projects(projects)
                return project
        return None

    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        projects = self._load_projects()
        original_count = len(projects)
        projects = [p for p in projects if p.id != project_id]

        if len(projects) < original_count:
            self._save_projects(projects)

            # 删除项目文件夹
            import shutil

            project_dir = self.projects_dir / project_id
            if project_dir.exists():
                shutil.rmtree(project_dir)

            return True
        return False

    def get_project_dir(self, project_id: str) -> Path:
        """获取项目目录"""
        return self.projects_dir / project_id

    def count_projects(self) -> int:
        """统计项目数量"""
        return len(self._load_projects())


# 全局存储实例
storage = ProjectStorage()
