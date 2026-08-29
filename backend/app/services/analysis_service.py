from typing import Dict, List


def detect_issues(features: Dict[str, float]) -> List[Dict]:
    issues = []

    sharpness = features.get("sharpness", 0)
    brightness = features.get("brightness", 128)
    contrast = features.get("contrast", 50)
    noise = features.get("noise", 0)
    dark_ratio = features.get("dark_pixel_ratio", 0)
    bright_ratio = features.get("bright_pixel_ratio", 0)
    saturation = features.get("saturation_ratio", 0)

    if sharpness < 100:
        severity = "HIGH" if sharpness < 30 else "MEDIUM" if sharpness < 60 else "LOW"
        confidence = min(1.0, (100 - sharpness) / 100)
        issues.append({
            "type": "BLUR",
            "severity": severity,
            "confidence": round(confidence, 2),
            "explanation": f"Sharpness score is {sharpness:.1f} (low Laplacian variance indicates possible blur). Images with sharpness below 100 are considered blurry."
        })
    elif sharpness < 200:
        confidence = min(1.0, (200 - sharpness) / 200 * 0.5)
        issues.append({
            "type": "BLUR",
            "severity": "LOW",
            "confidence": round(confidence, 2),
            "explanation": f"Sharpness score is {sharpness:.1f}, which is borderline. The image may have slight softness."
        })

    if dark_ratio > 0.4:
        severity = "HIGH" if dark_ratio > 0.6 else "MEDIUM"
        confidence = min(1.0, dark_ratio)
        issues.append({
            "type": "UNDEREXPOSURE",
            "severity": severity,
            "confidence": round(confidence, 2),
            "explanation": f"{dark_ratio*100:.1f}% of pixels are very dark (below threshold 30). This indicates significant underexposure."
        })
    elif dark_ratio > 0.2:
        confidence = min(1.0, (dark_ratio - 0.2) * 5)
        issues.append({
            "type": "UNDEREXPOSURE",
            "severity": "LOW",
            "confidence": round(confidence, 2),
            "explanation": f"{dark_ratio*100:.1f}% of pixels are very dark. The image appears somewhat underexposed."
        })

    if bright_ratio > 0.3:
        severity = "HIGH" if bright_ratio > 0.5 else "MEDIUM"
        confidence = min(1.0, bright_ratio)
        issues.append({
            "type": "OVEREXPOSURE",
            "severity": severity,
            "confidence": round(confidence, 2),
            "explanation": f"{bright_ratio*100:.1f}% of pixels are very bright (above threshold 225). This indicates significant overexposure."
        })
    elif bright_ratio > 0.15:
        confidence = min(1.0, (bright_ratio - 0.15) * 5)
        issues.append({
            "type": "OVEREXPOSURE",
            "severity": "LOW",
            "confidence": round(confidence, 2),
            "explanation": f"{bright_ratio*100:.1f}% of pixels are very bright. The image appears somewhat overexposed."
        })

    if noise > 200:
        severity = "HIGH" if noise > 500 else "MEDIUM"
        confidence = min(1.0, noise / 600)
        issues.append({
            "type": "NOISE",
            "severity": severity,
            "confidence": round(confidence, 2),
            "explanation": f"Noise level is {noise:.1f} (local variance estimate). This is significantly above the normal range."
        })
    elif noise > 100:
        confidence = min(1.0, (noise - 100) / 300)
        issues.append({
            "type": "NOISE",
            "severity": "LOW",
            "confidence": round(confidence, 2),
            "explanation": f"Noise level is {noise:.1f}, which is moderately elevated."
        })

    corruption_score = 0
    if sharpness < 10 and dark_ratio > 0.5:
        corruption_score += 0.4
    if contrast < 10 and noise > 300:
        corruption_score += 0.3
    if dark_ratio > 0.7 or bright_ratio > 0.7:
        corruption_score += 0.3

    if corruption_score > 0.3:
        issues.append({
            "type": "CORRUPTION",
            "severity": "HIGH" if corruption_score > 0.6 else "MEDIUM",
            "confidence": round(min(1.0, corruption_score), 2),
            "explanation": f"Multiple severe degradation signals detected (score: {corruption_score:.2f}). The image may be corrupted or heavily degraded."
        })

    defect_score = 0
    if contrast < 15 and sharpness > 500:
        defect_score += 0.3
    if saturation > 0.5:
        defect_score += 0.2
    if dark_ratio > 0.3 and bright_ratio > 0.3:
        defect_score += 0.3

    if defect_score > 0.3:
        issues.append({
            "type": "POTENTIAL_VISUAL_DEFECT",
            "severity": "MEDIUM" if defect_score > 0.5 else "LOW",
            "confidence": round(min(1.0, defect_score), 2),
            "explanation": f"Unusual visual characteristics detected (score: {defect_score:.2f}). This may indicate a visual defect or artifact."
        })

    return issues


def generate_explainability(features: Dict[str, float], ml_label: str, ml_confidence: float, quality_score: float) -> Dict:
    explanations = {
        "summary": [],
        "feature_analysis": {},
        "model_decision": {},
    }

    sharpness = features.get("sharpness", 0)
    brightness = features.get("brightness", 128)
    contrast = features.get("contrast", 50)
    noise = features.get("noise", 0)
    dark_ratio = features.get("dark_pixel_ratio", 0)
    bright_ratio = features.get("bright_pixel_ratio", 0)

    explanations["feature_analysis"]["sharpness"] = {
        "value": round(sharpness, 2),
        "assessment": "sharp" if sharpness > 300 else "moderate" if sharpness > 100 else "blurry",
        "detail": f"Laplacian variance of {sharpness:.1f} {'indicates good sharpness' if sharpness > 300 else 'suggests some blur' if sharpness > 100 else 'indicates significant blur'}."
    }
    explanations["feature_analysis"]["brightness"] = {
        "value": round(brightness, 2),
        "assessment": "well-exposed" if 80 < brightness < 180 else "dark" if brightness <= 80 else "bright",
        "detail": f"Mean grayscale intensity is {brightness:.1f} (out of 255). {'This is within normal range.' if 80 < brightness < 180 else 'The image appears ' + ('underexposed.' if brightness <= 80 else 'overexposed.')}"
    }
    explanations["feature_analysis"]["contrast"] = {
        "value": round(contrast, 2),
        "assessment": "good" if contrast > 40 else "low" if contrast > 15 else "very low",
        "detail": f"Standard deviation of {contrast:.1f} {'indicates good contrast' if contrast > 40 else 'suggests moderate contrast' if contrast > 15 else 'indicates very low contrast'}."
    }
    explanations["feature_analysis"]["noise"] = {
        "value": round(noise, 2),
        "assessment": "clean" if noise < 50 else "moderate" if noise < 150 else "noisy",
        "detail": f"Local variance estimate of {noise:.1f} {'suggests a clean image' if noise < 50 else 'indicates moderate noise' if noise < 150 else 'indicates significant noise'}."
    }
    explanations["feature_analysis"]["dark_pixel_ratio"] = {
        "value": round(dark_ratio, 4),
        "assessment": "normal" if dark_ratio < 0.1 else "elevated" if dark_ratio < 0.3 else "high",
        "detail": f"{dark_ratio*100:.1f}% of pixels are very dark."
    }
    explanations["feature_analysis"]["bright_pixel_ratio"] = {
        "value": round(bright_ratio, 4),
        "assessment": "normal" if bright_ratio < 0.1 else "elevated" if bright_ratio < 0.2 else "high",
        "detail": f"{bright_ratio*100:.1f}% of pixels are very bright."
    }

    explanations["model_decision"] = {
        "prediction": ml_label,
        "confidence": round(ml_confidence, 3),
        "detail": f"The ML model predicts '{ml_label}' with {ml_confidence*100:.1f}% confidence."
    }

    if ml_label == "ACCEPTABLE" and quality_score >= 75:
        explanations["summary"].append("The image meets acceptable quality standards.")
    elif ml_label == "DEGRADED":
        explanations["summary"].append("The image shows signs of quality degradation but may still be usable.")
    else:
        explanations["summary"].append("The image has significant quality issues that may render it unsuitable.")

    if sharpness < 100:
        explanations["summary"].append("Image has low sharpness, which indicates possible blur.")
    if dark_ratio > 0.2:
        explanations["summary"].append(f"{dark_ratio*100:.1f}% of pixels are highly dark, indicating possible underexposure.")
    if bright_ratio > 0.15:
        explanations["summary"].append(f"{bright_ratio*100:.1f}% of pixels are highly bright, indicating possible overexposure.")
    if noise > 100:
        explanations["summary"].append("Noise level is above the learned normal range.")

    explanations["quality_score_breakdown"] = {
        "ml_component": round(ml_confidence * 100, 1),
        "sharpness_component": round(min(100, (sharpness / 500) * 100), 1),
        "brightness_component": round(100 - abs(brightness - 128) / 128 * 100, 1),
        "contrast_component": round(min(100, (contrast / 80) * 100), 1),
        "noise_component": round(max(0, 100 - (noise / 100) * 100), 1),
        "final_score": quality_score,
    }

    return explanations
