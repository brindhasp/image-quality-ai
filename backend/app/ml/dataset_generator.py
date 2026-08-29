import os
import csv
import random
import numpy as np
import cv2
from pathlib import Path
from typing import List, Tuple


class RealWorldDatasetGenerator:
    def __init__(self, output_dir: str = "dataset"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_from_folder(self, image_folder: str, output_csv: str = "features.csv"):
        features_list = []
        image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

        for root, _, files in os.walk(image_folder):
            for file in files:
                if Path(file).suffix.lower() in image_extensions:
                    filepath = os.path.join(root, file)
                    try:
                        image = cv2.imread(filepath)
                        if image is None:
                            continue

                        features = self._extract_features(image)
                        features["filename"] = file
                        features["filepath"] = filepath
                        features["label"] = self._auto_label(features)
                        features_list.append(features)
                    except Exception as e:
                        print(f"Error processing {filepath}: {e}")

        if features_list:
            csv_path = os.path.join(self.output_dir, output_csv)
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=features_list[0].keys())
                writer.writeheader()
                writer.writerows(features_list)
            print(f"Generated {len(features_list)} samples to {csv_path}")

        return features_list

    def generate_synthetic_variations(self, base_images: List[np.ndarray], num_variations: int = 100):
        features_list = []

        for i in range(num_variations):
            base = random.choice(base_images)
            variation = self._apply_random_degradation(base)
            features = self._extract_features(variation)
            features["filename"] = f"synthetic_{i:04d}.png"
            features["label"] = self._auto_label(features)
            features_list.append(features)

        return features_list

    def _apply_random_degradation(self, image: np.ndarray) -> np.ndarray:
        result = image.copy()
        degradation_type = random.choice(["blur", "noise", "brightness", "contrast", "combined"])

        if degradation_type == "blur":
            kernel = random.choice([3, 5, 7])
            result = cv2.GaussianBlur(result, (kernel, kernel), 0)
        elif degradation_type == "noise":
            noise = np.random.normal(0, random.uniform(10, 50), result.shape).astype(np.float64)
            result = np.clip(result.astype(np.float64) + noise, 0, 255).astype(np.uint8)
        elif degradation_type == "brightness":
            factor = random.uniform(0.3, 0.7) if random.random() > 0.5 else random.uniform(1.3, 2.0)
            result = np.clip(result.astype(np.float64) * factor, 0, 255).astype(np.uint8)
        elif degradation_type == "contrast":
            factor = random.uniform(0.3, 0.7)
            gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
            mean = np.mean(gray)
            result = np.clip((result.astype(np.float64) - mean) * factor + mean, 0, 255).astype(np.uint8)
        elif degradation_type == "combined":
            result = cv2.GaussianBlur(result, (5, 5), 0)
            noise = np.random.normal(0, 20, result.shape).astype(np.float64)
            result = np.clip(result.astype(np.float64) * 0.6 + noise, 0, 255).astype(np.uint8)

        return result

    def _extract_features(self, image: np.ndarray) -> dict:
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
            saturation = hsv[:, :, 1]
            sat_ratio = float(np.sum(saturation > 240) / saturation.size) if saturation.size > 0 else 0.0
        else:
            sat_ratio = 0.0

        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.sum(edges > 0) / edges.size) if edges.size > 0 else 0.0

        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        texture = float(np.mean(np.sqrt(sobelx**2 + sobely**2)))

        return {
            "sharpness": round(sharpness, 2),
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "noise": round(noise, 2),
            "dark_pixel_ratio": round(dark_ratio, 4),
            "bright_pixel_ratio": round(bright_ratio, 4),
            "saturation_ratio": round(sat_ratio, 4),
            "edge_density": round(edge_density, 4),
            "texture_measure": round(texture, 2),
            "width": w,
            "height": h,
        }

    def _auto_label(self, features: dict) -> str:
        score = 0

        sharpness = features.get("sharpness", 0)
        if sharpness > 300:
            score += 30
        elif sharpness > 100:
            score += 15

        brightness = features.get("brightness", 128)
        if 80 < brightness < 180:
            score += 20

        contrast = features.get("contrast", 50)
        if contrast > 40:
            score += 20

        noise = features.get("noise", 0)
        if noise < 100:
            score += 15

        dark_ratio = features.get("dark_pixel_ratio", 0)
        bright_ratio = features.get("bright_pixel_ratio", 0)
        if dark_ratio < 0.2 and bright_ratio < 0.15:
            score += 15

        if score >= 70:
            return "ACCEPTABLE"
        elif score >= 40:
            return "DEGRADED"
        else:
            return "POTENTIALLY_DEFECTIVE"


if __name__ == "__main__":
    generator = RealWorldDatasetGenerator()
    print("Real-world dataset generator ready.")
    print("Usage: generator.generate_from_folder('/path/to/images')")
