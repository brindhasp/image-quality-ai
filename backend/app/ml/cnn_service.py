import numpy as np
from typing import Dict, Optional

try:
    import torch
    import torchvision.transforms as transforms
    from torchvision import models
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class CNNFeatureExtractor:
    def __init__(self):
        self.model = None
        self.preprocess = None
        self._loaded = False

    def load_model(self) -> bool:
        if not TORCH_AVAILABLE:
            return False
        try:
            self.model = models.resnet18(pretrained=True)
            self.model.eval()

            self.preprocess = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            self._loaded = True
            return True
        except Exception:
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self.model is not None

    def extract_features(self, image: np.ndarray) -> Dict[str, float]:
        if not self.is_loaded:
            return self._fallback_features(image)

        try:
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            input_tensor = self.preprocess(image)
            input_batch = input_tensor.unsqueeze(0)

            with torch.no_grad():
                features = self.model(input_batch)

            feature_vector = features.squeeze().numpy()

            return {
                "cnn_mean": float(np.mean(feature_vector)),
                "cnn_std": float(np.std(feature_vector)),
                "cnn_max": float(np.max(feature_vector)),
                "cnn_min": float(np.min(feature_vector)),
                "cnn_energy": float(np.sum(feature_vector ** 2)),
                "cnn_sparsity": float(np.mean(feature_vector == 0)),
            }
        except Exception:
            return self._fallback_features(image)

    def _fallback_features(self, image: np.ndarray) -> Dict[str, float]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        return {
            "cnn_mean": float(np.mean(gray)) / 255.0,
            "cnn_std": float(np.std(gray)) / 255.0,
            "cnn_max": float(np.max(gray)) / 255.0,
            "cnn_min": float(np.min(gray)) / 255.0,
            "cnn_energy": float(np.sum(gray.astype(float) ** 2)) / (gray.size * 255.0 * 255.0),
            "cnn_sparsity": float(np.mean(gray < 10)),
        }


try:
    import cv2
except ImportError:
    pass

cnn_service = CNNFeatureExtractor()
