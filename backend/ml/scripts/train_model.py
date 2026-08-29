"""
Train the Image Quality Classification model.

Usage:
    python ml/scripts/train_model.py [--samples N] [--output PATH]

Generates synthetic training data, trains a Random Forest classifier,
evaluates it, and saves the model + metrics.
"""

import os
import sys
import json
import argparse
import random
import numpy as np
import cv2
import joblib
from pathlib import Path
from datetime import datetime

# Add backend root to path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report
)
from sklearn.preprocessing import LabelEncoder


# ---------------------------------------------------------------------------
# Synthetic image generators
# ---------------------------------------------------------------------------

def create_base_images(size=256):
    """Create varied base images (gradients, patterns, textures)."""
    images = []

    # Horizontal gradient
    grad = np.zeros((size, size, 3), dtype=np.uint8)
    for i in range(size):
        grad[:, i] = [int(i / size * 255), int(i / size * 200), int((1 - i / size) * 255)]
    images.append(grad)

    # Checkerboard
    check = np.zeros((size, size, 3), dtype=np.uint8)
    block = size // 8
    for r in range(8):
        for c in range(8):
            if (r + c) % 2 == 0:
                check[r*block:(r+1)*block, c*block:(c+1)*block] = [200, 200, 200]
            else:
                check[r*block:(r+1)*block, c*block:(c+1)*block] = [50, 50, 50]
    images.append(check)

    # Circles
    circles = np.zeros((size, size, 3), dtype=np.uint8)
    for radius in range(20, size // 2, 30):
        cv2.circle(circles, (size // 2, size // 2), radius,
                   (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255)), 2)
    images.append(circles)

    # Random rectangles
    rects = np.ones((size, size, 3), dtype=np.uint8) * 128
    for _ in range(20):
        x1, y1 = random.randint(0, size - 50), random.randint(0, size - 50)
        x2, y2 = x1 + random.randint(20, 80), y1 + random.randint(20, 80)
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        cv2.rectangle(rects, (x1, y1), (x2, y2), color, -1)
    images.append(rects)

    # Noise texture base
    noise_img = np.random.randint(80, 200, (size, size, 3), dtype=np.uint8)
    noise_img = cv2.GaussianBlur(noise_img, (5, 5), 0)
    images.append(noise_img)

    # Vertical stripes
    stripes = np.zeros((size, size, 3), dtype=np.uint8)
    for i in range(0, size, 20):
        color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        stripes[:, i:i+10] = color
    images.append(stripes)

    # Diagonal pattern
    diag = np.zeros((size, size, 3), dtype=np.uint8)
    for i in range(-size, size * 2, 15):
        cv2.line(diag, (i, 0), (i + size, size), (180, 180, 180), 2)
    images.append(diag)

    # Solid color with subtle texture
    solid = np.ones((size, size, 3), dtype=np.uint8) * 140
    noise = np.random.normal(0, 10, solid.shape).astype(np.int16)
    solid = np.clip(solid.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    images.append(solid)

    return images


def apply_blur(image, severity="medium"):
    k = {"light": 3, "medium": 7, "heavy": 15, "extreme": 31}.get(severity, 7)
    return cv2.GaussianBlur(image, (k, k), 0)


def apply_noise(image, severity="medium"):
    sigma = {"light": 15, "medium": 35, "heavy": 55, "extreme": 80}.get(severity, 35)
    noise = np.random.normal(0, sigma, image.shape).astype(np.float64)
    return np.clip(image.astype(np.float64) + noise, 0, 255).astype(np.uint8)


def apply_darken(image, severity="medium"):
    factor = {"light": 0.6, "medium": 0.3, "heavy": 0.12, "extreme": 0.04}.get(severity, 0.3)
    return np.clip(image.astype(np.float64) * factor, 0, 255).astype(np.uint8)


def apply_brighten(image, severity="medium"):
    factor = {"light": 1.5, "medium": 2.2, "heavy": 3.0, "extreme": 4.0}.get(severity, 2.2)
    return np.clip(image.astype(np.float64) * factor, 0, 255).astype(np.uint8)


def apply_low_contrast(image, severity="medium"):
    factor = {"light": 0.6, "medium": 0.35, "heavy": 0.15, "extreme": 0.05}.get(severity, 0.35)
    mean = np.mean(image.astype(np.float64))
    return np.clip((image.astype(np.float64) - mean) * factor + mean, 0, 255).astype(np.uint8)


def apply_combined_degradation(image):
    result = apply_blur(image, "medium")
    result = apply_noise(result, "light")
    result = apply_darken(result, "light")
    return result


# ---------------------------------------------------------------------------
# Feature extraction (mirrors cv/feature_extraction.py)
# ---------------------------------------------------------------------------

def extract_features(image):
    if len(image.shape) == 2:
        gray = image
        hsv = None
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    h, w = gray.shape[:2]

    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = float(np.var(laplacian))
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    block_size = 8
    h_trim = (h // block_size) * block_size
    w_trim = (w // block_size) * block_size
    if h_trim > 0 and w_trim > 0:
        trimmed = gray[:h_trim, :w_trim].astype(np.float64)
        blocks = trimmed.reshape(h_trim // block_size, block_size, w_trim // block_size, block_size)
        blocks = blocks.transpose(0, 2, 1, 3)
        noise = float(np.mean(np.var(blocks, axis=(2, 3))))
    else:
        noise = 0.0

    total = gray.size
    dark_ratio = float(np.sum(gray < 30) / total) if total > 0 else 0.0
    bright_ratio = float(np.sum(gray > 225) / total) if total > 0 else 0.0

    if hsv is not None:
        sat = hsv[:, :, 1]
        sat_ratio = float(np.sum(sat > 240) / sat.size) if sat.size > 0 else 0.0
    else:
        sat_ratio = 0.0

    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.sum(edges > 0) / edges.size) if edges.size > 0 else 0.0

    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    texture = float(np.mean(np.sqrt(sobelx**2 + sobely**2)))

    return {
        "sharpness": sharpness,
        "brightness": brightness,
        "contrast": contrast,
        "noise": noise,
        "dark_pixel_ratio": dark_ratio,
        "bright_pixel_ratio": bright_ratio,
        "saturation_ratio": sat_ratio,
        "edge_density": edge_density,
        "texture_measure": texture,
    }


def label_from_features(features):
    score = 0
    if features["sharpness"] > 300:
        score += 30
    elif features["sharpness"] > 100:
        score += 15
    if 80 < features["brightness"] < 180:
        score += 20
    if features["contrast"] > 40:
        score += 20
    if features["noise"] < 100:
        score += 15
    if features["dark_pixel_ratio"] < 0.2 and features["bright_pixel_ratio"] < 0.15:
        score += 15

    if score >= 70:
        return "ACCEPTABLE"
    elif score >= 40:
        return "DEGRADED"
    else:
        return "POTENTIALLY_DEFECTIVE"


# ---------------------------------------------------------------------------
# Dataset generation
# ---------------------------------------------------------------------------

def generate_dataset(samples_per_class=200, seed=42):
    random.seed(seed)
    np.random.seed(seed)

    base_images = create_base_images(256)
    data = []
    labels = []

    degradations = {
        "ACCEPTABLE": [
            (lambda img: img, 1.0),
            (lambda img: apply_blur(img, "light"), 0.15),
            (lambda img: apply_noise(img, "light"), 0.15),
        ],
        "DEGRADED": [
            (lambda img: apply_blur(img, "medium"), 0.25),
            (lambda img: apply_noise(img, "medium"), 0.25),
            (lambda img: apply_darken(img, "light"), 0.2),
            (lambda img: apply_low_contrast(img, "medium"), 0.2),
            (lambda img: apply_combined_degradation(img), 0.1),
        ],
        "POTENTIALLY_DEFECTIVE": [
            (lambda img: apply_blur(img, "heavy"), 0.2),
            (lambda img: apply_noise(img, "heavy"), 0.2),
            (lambda img: apply_darken(img, "heavy"), 0.2),
            (lambda img: apply_brighten(img, "heavy"), 0.2),
            (lambda img: apply_low_contrast(img, "heavy"), 0.2),
        ],
    }

    for label, transforms in degradations.items():
        count = 0
        while count < samples_per_class:
            base = random.choice(base_images)
            transform_fn = random.choices(
                [t[0] for t in transforms],
                weights=[t[1] for t in transforms]
            )[0]
            degraded = transform_fn(base.copy())
            features = extract_features(degraded)
            assigned_label = label_from_features(features)

            # Accept if the auto-label matches our target (with some tolerance)
            if assigned_label == label or random.random() < 0.3:
                data.append([features[f] for f in [
                    "sharpness", "brightness", "contrast", "noise",
                    "dark_pixel_ratio", "bright_pixel_ratio", "saturation_ratio",
                    "edge_density", "texture_measure"
                ]])
                labels.append(label)
                count += 1

    return np.array(data), np.array(labels)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_model(X, y, output_path, metrics_path):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training set: {len(X_train)} samples")
    print(f"Test set:     {len(X_test)} samples")
    print(f"Classes:      {np.unique(y).tolist()}")
    print()

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=model.classes_).tolist()
    report = classification_report(y_test, y_pred, zero_division=0)

    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy", n_jobs=-1)

    print("=== Evaluation Results ===")
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print(f"CV Mean:   {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    print()
    print(report)

    # Feature importances
    feature_names = [
        "sharpness", "brightness", "contrast", "noise",
        "dark_pixel_ratio", "bright_pixel_ratio", "saturation_ratio",
        "edge_density", "texture_measure"
    ]
    importances = dict(zip(feature_names, [round(float(x), 4) for x in model.feature_importances_]))
    print("=== Feature Importances ===")
    for name, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True):
        print(f"  {name:25s} {imp:.4f}")

    # Save model
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(model, output_path)
    print(f"\nModel saved to: {output_path}")

    # Save metrics
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "cv_mean_accuracy": round(float(cv_scores.mean()), 4),
        "cv_std_accuracy": round(float(cv_scores.std()), 4),
        "confusion_matrix": cm,
        "classes": model.classes_.tolist(),
        "feature_importances": importances,
        "classification_report": report,
        "model_params": {
            "n_estimators": 200,
            "max_depth": 15,
            "min_samples_split": 5,
            "min_samples_leaf": 2,
            "class_weight": "balanced",
        },
    }

    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to: {metrics_path}")

    return model, metrics


def main():
    parser = argparse.ArgumentParser(description="Train image quality classifier")
    parser.add_argument("--samples", type=int, default=200, help="Samples per class")
    parser.add_argument("--output", type=str, default=None, help="Model output path")
    parser.add_argument("--metrics", type=str, default=None, help="Metrics output path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parent.parent.parent
    output_path = args.output or str(backend_dir / "models" / "image_quality_model.joblib")
    metrics_path = args.metrics or str(backend_dir / "ml" / "evaluation" / "metrics.json")

    print("=" * 60)
    print("  Image Quality Classifier - Training Pipeline")
    print("=" * 60)
    print()

    print("[1/3] Generating synthetic dataset...")
    X, y = generate_dataset(samples_per_class=args.samples, seed=args.seed)
    print(f"Generated {len(X)} samples ({len(np.unique(y))} classes)")
    print()

    print("[2/3] Training Random Forest model...")
    model, metrics = train_model(X, y, output_path, metrics_path)
    print()

    print("[3/3] Done!")
    print(f"  Model:  {output_path}")
    print(f"  Metrics: {metrics_path}")
    print()


if __name__ == "__main__":
    main()
