"""
客户聚类 API
"""
from fastapi import APIRouter, HTTPException
from backend.models.schemas import ClusteringRequest, ClusteringResponse
from backend.services.clustering_service import ClusteringService

router = APIRouter()
service = ClusteringService()


@router.post("/analyze/", response_model=ClusteringResponse)
async def cluster_customers(request: ClusteringRequest):
    """
    执行客户聚类分析

    - **n_clusters**: 聚类数量 (2-10)
    - **method**: 聚类方法 (kmeans/hierarchical)
    """
    try:
        result = await service.analyze(
            n_clusters=request.n_clusters,
            method=request.method
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/")
async def get_clustering_status():
    """获取聚类服务状态"""
    return {
        "success": True,
        "status": "ready",
        "message": "客户聚类服务正常运行"
    }
