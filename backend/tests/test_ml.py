import os
import sys
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.cv.feature_extraction import extract_features
from app.ml.service import ml_service, calculate_quality_score


def test_extract_features():
    img = np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)
    features = extract_features(img)

    assert isinstance(features, dict)
    expected_keys = [
        "sharpness", "brightness", "contrast", "noise",
        "dark_pixel_ratio", "bright_pixel_ratio", "saturation_ratio",
        "edge_density", "texture_measure", "width", "height", "aspect_ratio"
    ]
    for key in expected_keys:
        assert key in features, f"Missing feature: {key}"
        assert isinstance(features[key], float), f"Feature {key} should be float"


def test_extract_features_grayscale():
    gray = np.random.randint(0, 255, (128, 128), dtype=np.uint8)
    features = extract_features(gray)
    assert "sharpness" in features
    assert features["width"] == 128.0
    assert features["height"] == 128.0


def test_sharpness_high_for_sharp_image():
    sharp = np.zeros((128, 128, 3), dtype=np.uint8)
    sharp[::4, :, :] = 255
    features = extract_features(sharp)
    assert features["sharpness"] > 100


def test_sharpness_low_for_blurry_image():
    blurry = np.zeros((128, 128, 3), dtype=np.uint8)
    blurry[:, :, :] = 128
    features = extract_features(blurry)
    assert features["sharpness"] < 10


def test_brightness_range():
    img = np.ones((128, 128, 3), dtype=np.uint8) * 200
    features = extract_features(img)
    assert features["brightness"] > 150


def test_dark_pixel_ratio():
    dark = np.zeros((128, 128, 3), dtype=np.uint8)
    features = extract_features(dark)
    assert features["dark_pixel_ratio"] > 0.9


def test_bright_pixel_ratio():
    bright = np.ones((128, 128, 3), dtype=np.uint8) * 255
    features = extract_features(bright)
    assert features["bright_pixel_ratio"] > 0.9


def test_ml_service_predict():
    features = {
        "sharpness": 300.0,
        "brightness": 128.0,
        "contrast": 50.0,
        "noise": 30.0,
        "dark_pixel_ratio": 0.02,
        "bright_pixel_ratio": 0.01,
        "saturation_ratio": 0.01,
        "edge_density": 0.15,
        "texture_measure": 30.0,
    }
    label, confidence, prob_dict = ml_service.predict(features)
    assert label in ["ACCEPTABLE", "DEGRADED", "POTENTIALLY_DEFECTIVE"]
    assert 0 <= confidence <= 1
    assert isinstance(prob_dict, dict)


def test_ml_service_fallback():
    ml_service._loaded = False
    ml_service.model = None

    features = {
        "sharpness": 300.0,
        "brightness": 128.0,
        "contrast": 50.0,
        "noise": 30.0,
        "dark_pixel_ratio": 0.02,
        "bright_pixel_ratio": 0.01,
        "saturation_ratio": 0.01,
        "edge_density": 0.15,
        "texture_measure": 30.0,
    }
    label, confidence, prob_dict = ml_service.predict(features)
    assert label in ["ACCEPTABLE", "DEGRADED", "POTENTIALLY_DEFECTIVE"]


def test_calculate_quality_score():
    features = {
        "sharpness": 300.0,
        "brightness": 128.0,
        "contrast": 50.0,
        "noise": 30.0,
        "dark_pixel_ratio": 0.02,
        "bright_pixel_ratio": 0.01,
        "saturation_ratio": 0.01,
    }
    score = calculate_quality_score(features, "ACCEPTABLE", 0.8, {"ACCEPTABLE": 0.8})
    assert 0 <= score <= 100


def test_calculate_score_blurry():
    blurry_features = {
        "sharpness": 10.0,
        "brightness": 128.0,
        "contrast": 50.0,
        "noise": 30.0,
        "dark_pixel_ratio": 0.02,
        "bright_pixel_ratio": 0.01,
        "saturation_ratio": 0.01,
    }
    clean_features = {
        "sharpness": 500.0,
        "brightness": 128.0,
        "contrast": 50.0,
        "noise": 30.0,
        "dark_pixel_ratio": 0.02,
        "bright_pixel_ratio": 0.01,
        "saturation_ratio": 0.01,
    }
    blurry_score = calculate_quality_score(blurry_features, "DEGRADED", 0.7, {"DEGRADED": 0.7})
    clean_score = calculate_quality_score(clean_features, "ACCEPTABLE", 0.9, {"ACCEPTABLE": 0.9})
    assert blurry_score < clean_score
