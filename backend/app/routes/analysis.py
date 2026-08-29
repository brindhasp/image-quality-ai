import os
import uuid
import time
import logging
from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import numpy as np
import cv2

from app.config import settings
from app.database import get_db
from app.models import Analysis, Issue, ImageStatistics
from app.schemas import (
    AnalysisResponse, AnalysisListResponse, AnalysisListItem,
    StatisticsResponse, IssueResponse, ModelInfo, StatisticsSummary,
    BatchAnalysisResponse, ABTestResponse, ModelVersionInfo,
)
from app.cv.feature_extraction import extract_features
from app.ml.service import ml_service, calculate_quality_score
from app.services.analysis_service import detect_issues, generate_explainability

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    start_time = time.time()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    contents = await file.read()
    if len(contents) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(status_code=400, detail="Cannot decode image. File may be corrupted.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read image file")

    h, w = image.shape[:2]

    if max(h, w) > 4096:
        scale = 4096 / max(h, w)
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    features = extract_features(image)
    ml_label, ml_confidence, prob_dict = ml_service.predict(features)
    quality_score = calculate_quality_score(features, ml_label, ml_confidence, prob_dict)

    if quality_score >= 75:
        final_label = "ACCEPTABLE"
    elif quality_score >= 50:
        final_label = "DEGRADED"
    else:
        final_label = "POTENTIALLY_DEFECTIVE"

    issues = detect_issues(features)

    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    analysis = Analysis(
        filename=unique_filename,
        original_filename=file.filename,
        file_size=len(contents),
        width=w,
        height=h,
        quality_score=quality_score,
        quality_label=final_label,
        model_version=settings.MODEL_VERSION,
        created_at=datetime.now(timezone.utc),
    )
    db.add(analysis)
    db.flush()

    for issue in issues:
        db.add(Issue(
            analysis_id=analysis.id,
            type=issue["type"],
            severity=issue["severity"],
            confidence=issue["confidence"],
            explanation=issue["explanation"],
        ))

    db.add(ImageStatistics(
        analysis_id=analysis.id,
        sharpness=features["sharpness"],
        brightness=features["brightness"],
        contrast=features["contrast"],
        noise=features["noise"],
        dark_pixel_ratio=features["dark_pixel_ratio"],
        bright_pixel_ratio=features["bright_pixel_ratio"],
        saturation_ratio=features["saturation_ratio"],
        edge_density=features["edge_density"],
    ))
    db.commit()
    db.refresh(analysis)

    elapsed = time.time() - start_time
    logger.info(f"Analysis completed in {elapsed:.2f}s - {file.filename} -> {final_label} ({quality_score})")

    return AnalysisResponse(
        id=analysis.id,
        filename=analysis.original_filename,
        quality_score=analysis.quality_score,
        quality_label=analysis.quality_label,
        issues=[IssueResponse(type=i.type, severity=i.severity, confidence=i.confidence, explanation=i.explanation) for i in analysis.issues],
        statistics=StatisticsResponse(
            width=analysis.width,
            height=analysis.height,
            sharpness=analysis.statistics.sharpness,
            brightness=analysis.statistics.brightness,
            contrast=analysis.statistics.contrast,
            noise=analysis.statistics.noise,
            dark_pixel_ratio=analysis.statistics.dark_pixel_ratio,
            bright_pixel_ratio=analysis.statistics.bright_pixel_ratio,
            saturation_ratio=analysis.statistics.saturation_ratio,
            edge_density=analysis.statistics.edge_density,
        ),
        model=ModelInfo(name="RandomForestClassifier", version=settings.MODEL_VERSION),
        created_at=analysis.created_at,
    )


@router.get("/analyses", response_model=AnalysisListResponse)
def list_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query("", max_length=100),
    label: str = Query("", max_length=50),
    sort_by: str = Query("created_at", pattern="^(created_at|quality_score)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    query = db.query(Analysis)

    if search:
        query = query.filter(Analysis.original_filename.ilike(f"%{search}%"))
    if label:
        query = query.filter(Analysis.quality_label == label.upper())

    if sort_by == "quality_score":
        order_col = Analysis.quality_score
    else:
        order_col = Analysis.created_at

    if sort_order == "desc":
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return AnalysisListResponse(
        items=[
            AnalysisListItem(
                id=a.id,
                filename=a.original_filename,
                file_size=a.file_size,
                quality_score=a.quality_score,
                quality_label=a.quality_label,
                issues=[IssueResponse(type=i.type, severity=i.severity, confidence=i.confidence, explanation=i.explanation) for i in a.issues],
                created_at=a.created_at,
            )
            for a in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisResponse(
        id=analysis.id,
        filename=analysis.original_filename,
        quality_score=analysis.quality_score,
        quality_label=analysis.quality_label,
        issues=[IssueResponse(type=i.type, severity=i.severity, confidence=i.confidence, explanation=i.explanation) for i in analysis.issues],
        statistics=StatisticsResponse(
            width=analysis.width,
            height=analysis.height,
            sharpness=analysis.statistics.sharpness,
            brightness=analysis.statistics.brightness,
            contrast=analysis.statistics.contrast,
            noise=analysis.statistics.noise,
            dark_pixel_ratio=analysis.statistics.dark_pixel_ratio,
            bright_pixel_ratio=analysis.statistics.bright_pixel_ratio,
            saturation_ratio=analysis.statistics.saturation_ratio,
            edge_density=analysis.statistics.edge_density,
        ),
        model=ModelInfo(name="RandomForestClassifier", version=settings.MODEL_VERSION),
        created_at=analysis.created_at,
    )


@router.delete("/analyses/{analysis_id}")
def delete_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    db.delete(analysis)
    db.commit()
    return {"message": "Analysis deleted"}


@router.get("/statistics", response_model=StatisticsSummary)
def get_statistics(db: Session = Depends(get_db)):
    analyses = db.query(Analysis).all()
    if not analyses:
        return StatisticsSummary(
            total_analyses=0,
            average_score=0.0,
            acceptable_count=0,
            degraded_count=0,
            defective_count=0,
            most_common_issue=None,
            label_distribution={},
            issue_distribution={},
            recent_analyses=[],
        )

    total = len(analyses)
    avg_score = sum(a.quality_score for a in analyses) / total
    acceptable = sum(1 for a in analyses if a.quality_label == "ACCEPTABLE")
    degraded = sum(1 for a in analyses if a.quality_label == "DEGRADED")
    defective = sum(1 for a in analyses if a.quality_label == "POTENTIALLY_DEFECTIVE")

    label_dist = {}
    issue_count = {}
    for a in analyses:
        label_dist[a.quality_label] = label_dist.get(a.quality_label, 0) + 1
        for issue in a.issues:
            issue_count[issue.type] = issue_count.get(issue.type, 0) + 1

    most_common = max(issue_count, key=issue_count.get) if issue_count else None

    recent = sorted(analyses, key=lambda x: x.created_at, reverse=True)[:5]

    return StatisticsSummary(
        total_analyses=total,
        average_score=round(avg_score, 1),
        acceptable_count=acceptable,
        degraded_count=degraded,
        defective_count=defective,
        most_common_issue=most_common,
        label_distribution=label_dist,
        issue_distribution=issue_count,
        recent_analyses=[
            AnalysisListItem(
                id=a.id,
                filename=a.original_filename,
                file_size=a.file_size,
                quality_score=a.quality_score,
                quality_label=a.quality_label,
                issues=[IssueResponse(type=i.type, severity=i.severity, confidence=i.confidence, explanation=i.explanation) for i in a.issues],
                created_at=a.created_at,
            )
            for a in recent
        ],
    )


@router.get("/analyses/{analysis_id}/heatmap")
def get_heatmap(analysis_id: int, db: Session = Depends(get_db)):
    from app.cv.feature_extraction import generate_quality_heatmap

    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    upload_dir = settings.UPLOAD_DIR
    filepath = os.path.join(upload_dir, analysis.filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image file not found on disk")

    image = cv2.imread(filepath)
    if image is None:
        raise HTTPException(status_code=400, detail="Cannot read image file")

    heatmap = generate_quality_heatmap(image)

    import base64
    _, buffer = cv2.imencode(".png", heatmap)
    heatmap_b64 = base64.b64encode(buffer).decode("utf-8")

    return {
        "analysis_id": analysis_id,
        "heatmap_base64": heatmap_b64,
        "format": "png",
    }


@router.get("/model/info")
def get_model_info():
    return {
        "name": "RandomForestClassifier",
        "version": settings.MODEL_VERSION,
        "loaded": ml_service.is_loaded,
        "classes": ["ACCEPTABLE", "DEGRADED", "POTENTIALLY_DEFECTIVE"],
        "features": [
            "sharpness", "brightness", "contrast", "noise",
            "dark_pixel_ratio", "bright_pixel_ratio", "saturation_ratio",
            "edge_density", "texture_measure"
        ],
    }


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
async def analyze_batch(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    results = []
    errors = []

    for file in files:
        try:
            if not file.filename:
                errors.append({"filename": "unknown", "error": "No filename"})
                continue

            ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
            if ext not in settings.ALLOWED_EXTENSIONS:
                errors.append({"filename": file.filename, "error": f"Invalid file type '{ext}'"})
                continue

            contents = await file.read()
            if len(contents) > settings.max_upload_size_bytes:
                errors.append({"filename": file.filename, "error": "File too large"})
                continue

            if len(contents) == 0:
                errors.append({"filename": file.filename, "error": "Empty file"})
                continue

            nparr = np.frombuffer(contents, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                errors.append({"filename": file.filename, "error": "Cannot decode image"})
                continue

            h, w = image.shape[:2]
            if max(h, w) > 4096:
                scale = 4096 / max(h, w)
                image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

            features = extract_features(image)
            ml_label, ml_confidence, prob_dict = ml_service.predict(features)
            quality_score = calculate_quality_score(features, ml_label, ml_confidence, prob_dict)

            if quality_score >= 75:
                final_label = "ACCEPTABLE"
            elif quality_score >= 50:
                final_label = "DEGRADED"
            else:
                final_label = "POTENTIALLY_DEFECTIVE"

            issues = detect_issues(features)
            unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

            analysis = Analysis(
                filename=unique_filename,
                original_filename=file.filename,
                file_size=len(contents),
                width=w,
                height=h,
                quality_score=quality_score,
                quality_label=final_label,
                model_version=settings.MODEL_VERSION,
                created_at=datetime.now(timezone.utc),
            )
            db.add(analysis)
            db.flush()

            for issue in issues:
                db.add(Issue(
                    analysis_id=analysis.id,
                    type=issue["type"],
                    severity=issue["severity"],
                    confidence=issue["confidence"],
                    explanation=issue["explanation"],
                ))

            db.add(ImageStatistics(
                analysis_id=analysis.id,
                sharpness=features["sharpness"],
                brightness=features["brightness"],
                contrast=features["contrast"],
                noise=features["noise"],
                dark_pixel_ratio=features["dark_pixel_ratio"],
                bright_pixel_ratio=features["bright_pixel_ratio"],
                saturation_ratio=features["saturation_ratio"],
                edge_density=features["edge_density"],
            ))

            results.append(AnalysisResponse(
                id=analysis.id,
                filename=analysis.original_filename,
                quality_score=analysis.quality_score,
                quality_label=analysis.quality_label,
                issues=[IssueResponse(type=i.type, severity=i.severity, confidence=i.confidence, explanation=i.explanation) for i in analysis.issues],
                statistics=StatisticsResponse(
                    width=analysis.width,
                    height=analysis.height,
                    sharpness=analysis.statistics.sharpness,
                    brightness=analysis.statistics.brightness,
                    contrast=analysis.statistics.contrast,
                    noise=analysis.statistics.noise,
                    dark_pixel_ratio=analysis.statistics.dark_pixel_ratio,
                    bright_pixel_ratio=analysis.statistics.bright_pixel_ratio,
                    saturation_ratio=analysis.statistics.saturation_ratio,
                    edge_density=analysis.statistics.edge_density,
                ),
                model=ModelInfo(name="RandomForestClassifier", version=settings.MODEL_VERSION),
                created_at=analysis.created_at,
            ))
        except Exception as e:
            errors.append({"filename": file.filename if file.filename else "unknown", "error": str(e)})

    db.commit()

    return BatchAnalysisResponse(
        total=len(files),
        successful=len(results),
        failed=len(errors),
        results=results,
        errors=errors,
    )


@router.get("/ab/test/{analysis_id}", response_model=ABTestResponse)
def ab_test(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    stats = analysis.statistics
    features = {
        "sharpness": stats.sharpness,
        "brightness": stats.brightness,
        "contrast": stats.contrast,
        "noise": stats.noise,
        "dark_pixel_ratio": stats.dark_pixel_ratio,
        "bright_pixel_ratio": stats.bright_pixel_ratio,
        "saturation_ratio": stats.saturation_ratio,
        "edge_density": stats.edge_density,
        "texture_measure": 0.0,
    }

    label_a, conf_a, probs_a = ml_service.predict(features)

    from app.ml.service import MLService
    model_b = MLService()
    model_b.model_version = "fallback"
    label_b, conf_b, probs_b = model_b._fallback_prediction(features)

    return ABTestResponse(
        model_a=ModelInfo(name="RandomForestClassifier", version=settings.MODEL_VERSION),
        model_b=ModelInfo(name="RuleBasedFallback", version="1.0"),
        test_image_id=analysis_id,
        prediction_a={"label": label_a, "confidence": round(conf_a, 3), "probabilities": probs_a},
        prediction_b={"label": label_b, "confidence": round(conf_b, 3), "probabilities": probs_b},
        agreement=label_a == label_b,
    )


@router.get("/models/versions", response_model=List[ModelVersionInfo])
def get_model_versions(db: Session = Depends(get_db)):
    from sqlalchemy import func
    versions = db.query(
        Analysis.model_version,
        func.count(Analysis.id).label("total_predictions"),
    ).group_by(Analysis.model_version).all()

    return [
        ModelVersionInfo(
            version=v.model_version,
            loaded=(v.model_version == settings.MODEL_VERSION),
            total_predictions=v.total_predictions,
        )
        for v in versions
    ]
