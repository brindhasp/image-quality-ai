from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import io

from ..core.database import get_db, AnalysisResult
from ..core.config import settings
from ..services.quality_model import QualityClassifier

router = APIRouter()
classifier = QualityClassifier()

@router.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    
    try:
        image = Image.open(io.BytesIO(contents))
        image_np = np.array(image)
        
        if len(image_np.shape) == 2:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)
        elif image_np.shape[2] == 4:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2BGR)
        else:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Cannot read image: {str(e)}")
    
    file_path = settings.UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(contents)
    
    result = classifier.analyze_image(image_np)
    
    db_result = AnalysisResult(
        filename=file.filename,
        file_path=str(file_path),
        quality_score=result["quality_score"],
        quality_label=result["quality_label"],
        issues=result["issues"],
        statistics=result["statistics"]
    )
    
    db.add(db_result)
    await db.commit()
    await db.refresh(db_result)
    
    return {
        "id": db_result.id,
        "filename": file.filename,
        "quality_score": result["quality_score"],
        "quality_label": result["quality_label"],
        "issues": result["issues"],
        "statistics": result["statistics"],
        "confidence": result.get("confidence", 0.0),
        "created_at": db_result.created_at.isoformat() if db_result.created_at else None
    }

@router.get("/analyses")
@router.get("/history")
async def get_history(
    page: int = 1,
    page_size: int = 10,
    search: str = "",
    label: str = "",
    sort_by: str = "created_at",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    query = select(AnalysisResult)

    if search:
        query = query.where(AnalysisResult.filename.ilike(f"%{search}%"))
    if label:
        query = query.where(AnalysisResult.quality_label == label)

    sort_col = getattr(AnalysisResult, sort_by, AnalysisResult.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    from sqlalchemy import func
    count_query = select(func.count()).select_from(AnalysisResult)
    if search:
        count_query = count_query.where(AnalysisResult.filename.ilike(f"%{search}%"))
    if label:
        count_query = count_query.where(AnalysisResult.quality_label == label)
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    analyses = result.scalars().all()

    total_pages = max(1, (total + page_size - 1) // page_size)

    return {
        "items": [a.to_dict() for a in analyses],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }

@router.get("/analyses/{analysis_id}")
@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis.to_dict()

@router.delete("/analyses/{analysis_id}")
@router.delete("/analysis/{analysis_id}")
async def delete_analysis(analysis_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    file_path = Path(analysis.file_path)
    if file_path.exists():
        file_path.unlink()
    
    await db.delete(analysis)
    await db.commit()
    
    return {"message": "Analysis deleted successfully"}

@router.get("/statistics")
async def get_statistics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AnalysisResult).order_by(AnalysisResult.created_at.desc())
    )
    analyses = result.scalars().all()

    total = len(analyses)
    if total == 0:
        return {
            "total_analyses": 0,
            "average_score": 0,
            "acceptable_count": 0,
            "degraded_count": 0,
            "defective_count": 0,
            "most_common_issue": None,
            "label_distribution": {},
            "issue_distribution": {},
            "recent_analyses": [],
        }

    scores = [a.quality_score for a in analyses]
    avg_score = round(sum(scores) / len(scores), 1)

    label_dist = {}
    issue_dist = {}
    acceptable = 0
    degraded = 0
    defective = 0

    for a in analyses:
        label = a.quality_label
        label_dist[label] = label_dist.get(label, 0) + 1
        if label == "acceptable":
            acceptable += 1
        elif label == "degraded":
            degraded += 1
        elif label == "defective":
            defective += 1

        issues = a.issues if isinstance(a.issues, list) else []
        for issue in issues:
            if isinstance(issue, dict):
                name = issue.get("type", issue.get("name", "unknown"))
            else:
                name = str(issue)
            issue_dist[name] = issue_dist.get(name, 0) + 1

    most_common_issue = max(issue_dist, key=issue_dist.get) if issue_dist else None

    recent = [a.to_dict() for a in analyses[:10]]

    return {
        "total_analyses": total,
        "average_score": avg_score,
        "acceptable_count": acceptable,
        "degraded_count": degraded,
        "defective_count": defective,
        "most_common_issue": most_common_issue,
        "label_distribution": label_dist,
        "issue_distribution": issue_dist,
        "recent_analyses": recent,
    }


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "model_loaded": classifier.model_path.exists()
    }