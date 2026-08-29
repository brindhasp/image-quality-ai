import numpy as np
import pickle
from pathlib import Path
from typing import Dict, List, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import cv2
import json
from ..core.config import settings
from .feature_extractor import FeatureExtractor

class QualityClassifier:
    def __init__(self):
        self.scaler = StandardScaler()
        self.classifier = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.feature_extractor = FeatureExtractor()
        self.model_path = settings.MODEL_DIR / "quality_model.pkl"
        self.label_map = {
            0: "ACCEPTABLE",
            1: "BLUR",
            2: "UNDEREXPOSED",
            3: "OVEREXPOSED",
            4: "NOISY",
            5: "DEFECTIVE"
        }
        self.issue_map = {
            0: [],
            1: [{"type": "blur", "severity": "high", "confidence": 0.9}],
            2: [{"type": "underexposure", "severity": "high", "confidence": 0.85}],
            3: [{"type": "overexposure", "severity": "high", "confidence": 0.85}],
            4: [{"type": "noise", "severity": "medium", "confidence": 0.8}],
            5: [{"type": "corruption", "severity": "critical", "confidence": 0.9}]
        }
    
    def features_to_vector(self, features) -> np.ndarray:
        base_features = np.array([
            features.sharpness,
            features.brightness,
            features.contrast,
            features.noise_level,
            features.saturation,
            features.exposure_score,
            features.blur_score
        ])
        texture = features.texture_features if features.texture_features is not None else np.zeros(5)
        return np.concatenate([base_features, texture])
    
    def analyze_image(self, image: np.ndarray) -> Dict:
        features = self.feature_extractor.extract_all_features(image)
        feature_vector = self.features_to_vector(features)
        
        if self.model_path.exists():
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
                self.classifier = model_data['classifier']
                self.scaler = model_data['scaler']
            
            scaled_features = self.scaler.transform(feature_vector.reshape(1, -1))
            prediction = self.classifier.predict(scaled_features)[0]
            confidence = float(np.max(self.classifier.predict_proba(scaled_features)))
        else:
            prediction, confidence = self._rule_based_analysis(features)
        
        issues = self._detect_issues(features, prediction, confidence)
        quality_score = self._calculate_quality_score(features, prediction)
        
        statistics = {
            "sharpness": round(features.sharpness, 3),
            "brightness": round(features.brightness, 3),
            "contrast": round(features.contrast, 3),
            "noise_level": round(features.noise_level, 3),
            "saturation": round(features.saturation, 3),
            "exposure_score": round(features.exposure_score, 3),
            "blur_score": round(features.blur_score, 3)
        }
        
        return {
            "quality_score": quality_score,
            "quality_label": self.label_map.get(prediction, "UNKNOWN"),
            "issues": issues,
            "statistics": statistics,
            "confidence": confidence
        }
    
    def _rule_based_analysis(self, features) -> Tuple[int, float]:
        issues = []
        scores = []
        
        if features.blur_score > 0.6:
            issues.append(1)
            scores.append(features.blur_score)
        
        if features.brightness < 0.3:
            issues.append(2)
            scores.append(1.0 - features.brightness)
        elif features.brightness > 0.7:
            issues.append(3)
            scores.append(features.brightness)
        
        if features.noise_level > 0.4:
            issues.append(4)
            scores.append(features.noise_level)
        
        if features.contrast < 0.2:
            issues.append(5)
            scores.append(1.0 - features.contrast)
        
        if not issues:
            return 0, 0.75
        
        primary_issue = issues[np.argmax(scores)]
        confidence = 0.6 + 0.3 * max(scores)
        
        return primary_issue, min(confidence, 0.95)
    
    def _detect_issues(self, features, prediction: int, confidence: float) -> List[Dict]:
        issues = []
        
        if features.blur_score > 0.5:
            severity = "high" if features.blur_score > 0.7 else "medium"
            issues.append({
                "type": "blur",
                "severity": severity,
                "confidence": round(min(features.blur_score * 1.2, 0.99), 2),
                "description": "Image appears blurry or lacks sharpness"
            })
        
        if features.brightness < 0.35:
            severity = "high" if features.brightness < 0.2 else "medium"
            issues.append({
                "type": "underexposure",
                "severity": severity,
                "confidence": round(min((1.0 - features.brightness) * 1.1, 0.99), 2),
                "description": "Image is too dark (underexposed)"
            })
        
        if features.brightness > 0.65:
            severity = "high" if features.brightness > 0.8 else "medium"
            issues.append({
                "type": "overexposure",
                "severity": severity,
                "confidence": round(min(features.brightness * 1.2, 0.99), 2),
                "description": "Image is too bright (overexposed)"
            })
        
        if features.noise_level > 0.35:
            severity = "high" if features.noise_level > 0.5 else "medium"
            issues.append({
                "type": "noise",
                "severity": severity,
                "confidence": round(min(features.noise_level * 1.3, 0.99), 2),
                "description": "Image contains significant noise"
            })
        
        if features.contrast < 0.25:
            severity = "medium" if features.contrast > 0.15 else "high"
            issues.append({
                "type": "low_contrast",
                "severity": severity,
                "confidence": round(min((1.0 - features.contrast) * 0.9, 0.99), 2),
                "description": "Image has low contrast"
            })
        
        if not issues:
            issues.append({
                "type": "none",
                "severity": "none",
                "confidence": 0.9,
                "description": "No significant quality issues detected"
            })
        
        return issues
    
    def _calculate_quality_score(self, features, prediction: int) -> int:
        score = 100
        
        if features.blur_score > 0.5:
            score -= int(features.blur_score * 40)
        
        if features.brightness < 0.35 or features.brightness > 0.65:
            brightness_penalty = abs(features.brightness - 0.5) * 60
            score -= int(brightness_penalty)
        
        if features.noise_level > 0.35:
            score -= int(features.noise_level * 35)
        
        if features.contrast < 0.25:
            score -= int((0.25 - features.contrast) * 100)
        
        return max(0, min(100, score))
    
    def train_model(self, X: np.ndarray, y: np.ndarray) -> Dict:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.classifier.fit(X_train_scaled, y_train)
        
        y_pred = self.classifier.predict(X_test_scaled)
        
        unique_labels = sorted(set(y))
        target_names = [self.label_map[i] for i in unique_labels]
        report = classification_report(y_test, y_pred, labels=unique_labels, target_names=target_names)
        cm = confusion_matrix(y_test, y_pred, labels=unique_labels)
        
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'classifier': self.classifier,
                'scaler': self.scaler
            }, f)
        
        return {
            "accuracy": float(np.mean(y_pred == y_test)),
            "report": report,
            "confusion_matrix": cm.tolist()
        }
    
    def generate_training_data(self, num_samples_per_class: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        X = []
        y = []
        
        for _ in range(num_samples_per_class):
            clean_img = np.random.randint(100, 200, (256, 256, 3), dtype=np.uint8)
            features = self.feature_extractor.extract_all_features(clean_img)
            X.append(self.features_to_vector(features))
            y.append(0)
            
            blur_img = cv2.GaussianBlur(clean_img, (21, 21), 0)
            features = self.feature_extractor.extract_all_features(blur_img)
            X.append(self.features_to_vector(features))
            y.append(1)
            
            dark_img = np.clip(clean_img * 0.3, 0, 255).astype(np.uint8)
            features = self.feature_extractor.extract_all_features(dark_img)
            X.append(self.features_to_vector(features))
            y.append(2)
            
            bright_img = np.clip(clean_img * 2.0, 0, 255).astype(np.uint8)
            features = self.feature_extractor.extract_all_features(bright_img)
            X.append(self.features_to_vector(features))
            y.append(3)
            
            noise = np.random.normal(0, 50, clean_img.shape).astype(np.float32)
            noisy_img = np.clip(clean_img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
            features = self.feature_extractor.extract_all_features(noisy_img)
            X.append(self.features_to_vector(features))
            y.append(4)
            
            defect_img = clean_img.copy()
            defect_img[100:200, 100:200] = 0
            defect_img[50:150, 200:300] = 255
            defect_img = cv2.GaussianBlur(defect_img, (15, 15), 0)
            defect_img = np.clip(defect_img.astype(np.float32) * 0.5, 0, 255).astype(np.uint8)
            features = self.feature_extractor.extract_all_features(defect_img)
            X.append(self.features_to_vector(features))
            y.append(5)
        
        return np.array(X), np.array(y)