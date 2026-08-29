import os
import joblib
import numpy as np
from typing import Dict, Tuple

from app.config import settings


class MLService:
    def __init__(self):
        self.model = None
        self.model_version = settings.MODEL_VERSION
        self._loaded = False

    def load_model(self) -> bool:
        model_path = settings.MODEL_PATH
        if not os.path.exists(model_path):
            return False
        try:
            self.model = joblib.load(model_path)
            self._loaded = True
            return True
        except Exception:
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self.model is not None

    def predict(self, features: Dict[str, float]) -> Tuple[str, float, Dict[str, float]]:
        if not self.is_loaded:
            return self._fallback_prediction(features)

        feature_names = [
            "sharpness", "brightness", "contrast", "noise",
            "dark_pixel_ratio", "bright_pixel_ratio", "saturation_ratio",
            "edge_density", "texture_measure"
        ]
        feature_vector = np.array([[features.get(f, 0.0) for f in feature_names]])

        prediction = self.model.predict(feature_vector)[0]
        probabilities = self.model.predict_proba(feature_vector)[0]
        classes = self.model.classes_

        prob_dict = {cls: float(prob) for cls, prob in zip(classes, probabilities)}
        confidence = float(max(probabilities))

        return str(prediction), confidence, prob_dict

    def _fallback_prediction(self, features: Dict[str, float]) -> Tuple[str, float, Dict[str, float]]:
        score = calculate_quality_score(features, "ACCEPTABLE", 0.5, {})
        if score >= 75:
            label = "ACCEPTABLE"
        elif score >= 50:
            label = "DEGRADED"
        else:
            label = "POTENTIALLY_DEFECTIVE"
        return label, 0.5, {label: 0.5}


def calculate_quality_score(
    features: Dict[str, float],
    ml_label: str,
    ml_confidence: float,
    prob_dict: Dict[str, float],
) -> float:
    sharpness = features.get("sharpness", 0)
    brightness = features.get("brightness", 128)
    contrast = features.get("contrast", 50)
    noise = features.get("noise", 0)
    dark_ratio = features.get("dark_pixel_ratio", 0)
    bright_ratio = features.get("bright_pixel_ratio", 0)

    sharpness_score = min(100, (sharpness / 500) * 100)
    brightness_score = 100 - abs(brightness - 128) / 128 * 100
    contrast_score = min(100, (contrast / 80) * 100)
    noise_score = max(0, 100 - (noise / 100) * 100)
    exposure_score = max(0, min(100, 100 - (dark_ratio + bright_ratio) * 200))

    cv_score = (
        sharpness_score * 0.25
        + brightness_score * 0.15
        + contrast_score * 0.15
        + noise_score * 0.20
        + exposure_score * 0.25
    )

    ml_weight = 0.6
    cv_weight = 0.4

    if ml_label == "ACCEPTABLE":
        ml_score = prob_dict.get("ACCEPTABLE", 0.5) * 100
    elif ml_label == "DEGRADED":
        ml_score = 50 + prob_dict.get("DEGRADED", 0.5) * 25
    else:
        ml_score = prob_dict.get("POTENTIALLY_DEFECTIVE", 0.5) * 50

    final_score = ml_score * ml_weight + cv_score * cv_weight
    return round(max(0, min(100, final_score)), 1)


ml_service = MLService()
