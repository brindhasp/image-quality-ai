import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.quality_model import QualityClassifier
import numpy as np

def train():
    print("Generating training data...")
    classifier = QualityClassifier()
    X, y = classifier.generate_training_data(num_samples_per_class=200)
    
    print(f"Training data shape: {X.shape}")
    print(f"Labels distribution: {np.bincount(y)}")
    
    print("Training model...")
    results = classifier.train_model(X, y)
    
    print(f"\nTraining Results:")
    print(f"Accuracy: {results['accuracy']:.4f}")
    print(f"\nClassification Report:\n{results['report']}")
    print(f"\nConfusion Matrix:\n{np.array(results['confusion_matrix'])}")

if __name__ == "__main__":
    train()