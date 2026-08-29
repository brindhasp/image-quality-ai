import os
import sys
import gc
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.database import Base, get_db

TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(autouse=True)
def setup_database():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    gc.collect()
    try:
        if os.path.exists("test.db"):
            os.remove("test.db")
    except PermissionError:
        pass


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_image_bytes():
    import numpy as np
    import cv2
    img = np.random.randint(50, 200, (128, 128, 3), dtype=np.uint8)
    _, buffer = cv2.imencode(".png", img)
    return buffer.tobytes()


@pytest.fixture
def blur_image_bytes():
    import numpy as np
    import cv2
    img = np.random.randint(50, 200, (128, 128, 3), dtype=np.uint8)
    blurred = cv2.GaussianBlur(img, (21, 21), 0)
    _, buffer = cv2.imencode(".png", blurred)
    return buffer.tobytes()
