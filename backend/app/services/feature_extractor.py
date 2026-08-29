import cv2
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class ImageFeatures:
    sharpness: float
    brightness: float
    contrast: float
    noise_level: float
    saturation: float
    exposure_score: float
    blur_score: float
    color_histogram: np.ndarray
    texture_features: np.ndarray

class FeatureExtractor:
    
    def extract_all_features(self, image: np.ndarray) -> ImageFeatures:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        return ImageFeatures(
            sharpness=self._calculate_sharpness(gray),
            brightness=self._calculate_brightness(gray),
            contrast=self._calculate_contrast(gray),
            noise_level=self._estimate_noise(gray),
            saturation=self._calculate_saturation(image),
            exposure_score=self._calculate_exposure(gray),
            blur_score=self._calculate_blur_score(gray),
            color_histogram=self._calculate_color_histogram(image),
            texture_features=self._extract_texture_features(gray)
        )
    
    def _calculate_sharpness(self, gray: np.ndarray) -> float:
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        normalized = min(variance / 1000.0, 1.0)
        return float(normalized)
    
    def _calculate_brightness(self, gray: np.ndarray) -> float:
        return float(np.mean(gray) / 255.0)
    
    def _calculate_contrast(self, gray: np.ndarray) -> float:
        return float(np.std(gray) / 128.0)
    
    def _estimate_noise(self, gray: np.ndarray) -> float:
        h, w = gray.shape
        M = [
            [1, -2, 1],
            [-2, 4, -2],
            [1, -2, 1]
        ]
        sigma = np.sum(np.abs(cv2.filter2D(gray.astype(np.float64), -1, np.array(M))))
        sigma = sigma * np.sqrt(0.5 * np.pi) / (6 * (w - 2) * (h - 2))
        normalized = min(sigma / 50.0, 1.0)
        return float(normalized)
    
    def _calculate_saturation(self, image: np.ndarray) -> float:
        if len(image.shape) < 3 or image.shape[2] < 3:
            return 0.0
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        return float(np.mean(hsv[:, :, 1]) / 255.0)
    
    def _calculate_exposure(self, gray: np.ndarray) -> float:
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / hist.sum()
        
        dark_pixels = np.sum(hist[:50])
        bright_pixels = np.sum(hist[205:])
        
        if dark_pixels > 0.5:
            return 0.2  # Underexposed
        elif bright_pixels > 0.5:
            return 0.8  # Overexposed
        else:
            return 0.5  # Good exposure
    
    def _calculate_blur_score(self, gray: np.ndarray) -> float:
        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.sum(edges > 0) / edges.size
        normalized = min(edge_density * 5.0, 1.0)
        return float(1.0 - normalized)
    
    def _calculate_color_histogram(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) < 3:
            hist = cv2.calcHist([image], [0], None, [64], [0, 256])
        else:
            hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist = hist.flatten() / hist.sum()
        return hist
    
    def _extract_texture_features(self, gray: np.ndarray) -> np.ndarray:
        from skimage.feature import graycomatrix, graycoprops
        
        glcm = graycomatrix(gray, distances=[1], angles=[0], levels=256, symmetric=True, normed=True)
        
        contrast = graycoprops(glcm, 'contrast')[0, 0]
        dissimilarity = graycoprops(glcm, 'dissimilarity')[0, 0]
        homogeneity = graycoprops(glcm, 'homogeneity')[0, 0]
        energy = graycoprops(glcm, 'energy')[0, 0]
        correlation = graycoprops(glcm, 'correlation')[0, 0]
        
        features = np.array([
            contrast / 1000.0,
            dissimilarity / 50.0,
            homogeneity,
            energy,
            (correlation + 1) / 2.0
        ])
        return np.clip(features, 0, 1)