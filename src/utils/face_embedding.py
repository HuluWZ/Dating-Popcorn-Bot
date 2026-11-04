"""
Local face embeddings (OpenCV YuNet detector + SFace recognizer, both small ONNX models).
Embeddings are stored in Postgres (pgvector) and compared with cosine similarity.
"""

import logging
import tempfile
import threading
from pathlib import Path
from typing import List

import cv2
import numpy as np
import requests

logger = logging.getLogger(__name__)

_ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"
_DETECTOR_URL = f"{_ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx"
_RECOGNIZER_URL = f"{_ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx"
_MODEL_DIR = Path(tempfile.gettempdir()) / "popcorn-face-models"

# Recommended SFace cosine threshold from the OpenCV Zoo docs
COSINE_MATCH_THRESHOLD = 0.363
# Faces smaller than this (pixels) or detected with less confidence are rejected
MIN_FACE_SIZE = 80
MIN_FACE_SCORE = 0.8
EMBEDDING_DIM = 128
MAX_IMAGE_BYTES = 15 * 1024 * 1024

_lock = threading.Lock()
_models = None


class FaceDetectionError(Exception):
    """error_code is one of the codes search_flow maps to user messages"""
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        super().__init__(message)


def _fetch(url: str) -> str:
    path = _MODEL_DIR / url.rsplit("/", 1)[1]
    if not path.exists():
        _MODEL_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading face model %s", url)
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        tmp = path.with_suffix(".part")
        tmp.write_bytes(response.content)
        tmp.replace(path)  # atomic, so a crashed download never leaves a truncated model
    return str(path)


def _get_models():
    global _models
    with _lock:
        if _models is None:
            detector = cv2.FaceDetectorYN.create(_fetch(_DETECTOR_URL), "", (320, 320), MIN_FACE_SCORE)
            recognizer = cv2.FaceRecognizerSF.create(_fetch(_RECOGNIZER_URL), "")
            _models = (detector, recognizer)
        return _models


def embed_face(image_bytes: bytes) -> List[float]:
    """Return the L2-normalized 128-d embedding of the largest face. Blocking: call via asyncio.to_thread."""
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise FaceDetectionError("IMAGE_TOO_LARGE", "Image is too large.")
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FaceDetectionError("INVALID_IMAGE", "Could not decode image.")

    detector, recognizer = _get_models()
    with _lock:  # the detector keeps per-call input-size state
        detector.setInputSize((image.shape[1], image.shape[0]))
        _, faces = detector.detect(image)
        if faces is None or len(faces) == 0:
            raise FaceDetectionError("NO_FACE", "No face detected in the image.")
        face = max(faces, key=lambda f: f[2] * f[3])
        if min(face[2], face[3]) < MIN_FACE_SIZE:
            raise FaceDetectionError("FACE_TOO_SMALL_OR_LOW_QUALITY", "Face is too small.")
        feature = recognizer.feature(recognizer.alignCrop(image, face))

    vector = feature.flatten().astype(np.float64)
    return (vector / np.linalg.norm(vector)).tolist()
