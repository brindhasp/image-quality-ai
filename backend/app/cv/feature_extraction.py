import cv2
import numpy as np
from typing import Dict


def extract_features(image: np.ndarray) -> Dict[str, float]:
    if len(image.shape) == 2:
        gray = image
        hsv = None
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    h, w = gray.shape[:2]

    return {
        "sharpness": compute_sharpness(gray),
        "brightness": compute_brightness(gray),
        "contrast": compute_contrast(gray),
        "noise": compute_noise_estimate(gray),
        "dark_pixel_ratio": compute_dark_pixel_ratio(gray),
        "bright_pixel_ratio": compute_bright_pixel_ratio(gray),
        "saturation_ratio": compute_saturation_ratio(hsv) if hsv is not None else 0.0,
        "edge_density": compute_edge_density(gray),
        "texture_measure": compute_texture_measure(gray),
        "width": float(w),
        "height": float(h),
        "aspect_ratio": float(w / h) if h > 0 else 0.0,
    }


def compute_sharpness(gray: np.ndarray) -> float:
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(np.var(laplacian))


def compute_brightness(gray: np.ndarray) -> float:
    return float(np.mean(gray))


def compute_contrast(gray: np.ndarray) -> float:
    return float(np.std(gray))


def compute_noise_estimate(gray: np.ndarray) -> float:
    h, w = gray.shape[:2]
    block_size = 8
    h_trim = (h // block_size) * block_size
    w_trim = (w // block_size) * block_size
    if h_trim == 0 or w_trim == 0:
        return 0.0
    trimmed = gray[:h_trim, :w_trim].astype(np.float64)
    blocks = trimmed.reshape(h_trim // block_size, block_size, w_trim // block_size, block_size)
    blocks = blocks.transpose(0, 2, 1, 3)
    variances = np.var(blocks, axis=(2, 3))
    return float(np.mean(variances))


def compute_dark_pixel_ratio(gray: np.ndarray, threshold: int = 30) -> float:
    total = gray.size
    dark = np.sum(gray < threshold)
    return float(dark / total) if total > 0 else 0.0


def compute_bright_pixel_ratio(gray: np.ndarray, threshold: int = 225) -> float:
    total = gray.size
    bright = np.sum(gray > threshold)
    return float(bright / total) if total > 0 else 0.0


def compute_saturation_ratio(hsv: np.ndarray) -> float:
    if hsv is None or len(hsv.shape) < 3:
        return 0.0
    saturation = hsv[:, :, 1]
    total = saturation.size
    saturated = np.sum(saturation > 240)
    return float(saturated / total) if total > 0 else 0.0


def compute_edge_density(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 50, 150)
    return float(np.sum(edges > 0) / edges.size) if edges.size > 0 else 0.0


def compute_texture_measure(gray: np.ndarray) -> float:
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(sobelx**2 + sobely**2)
    return float(np.mean(magnitude))


def generate_quality_heatmap(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    h, w = gray.shape[:2]
    block = 32
    heatmap = np.zeros((h, w), dtype=np.float64)

    for y in range(0, h - block, block):
        for x in range(0, w - block, block):
            roi = gray[y:y+block, x:x+block]
            lap_var = float(np.var(cv2.Laplacian(roi, cv2.CV_64F)))
            local_noise = float(np.var(roi.astype(np.float64)))
            brightness = float(np.mean(roi))
            exposure_penalty = abs(brightness - 128) / 128
            sharpness_norm = min(1.0, lap_var / 500)
            noise_penalty = min(1.0, local_noise / 200)
            score = sharpness_norm * 0.4 + (1 - exposure_penalty) * 0.3 + (1 - noise_penalty) * 0.3
            heatmap[y:y+block, x:x+block] = score

    heatmap = np.clip(heatmap, 0, 1)
    heatmap = (heatmap * 255).astype(np.uint8)
    heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    return heatmap
