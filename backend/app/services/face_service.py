from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np

@dataclass(frozen=True)
class FaceCheck:
    ok: bool
    code: str
    embedding: np.ndarray | None = None
    quality_score: float = 0.0

class FaceService:
    """CPU-only YuNet/SFace quality and embedding pipeline; missing models fail closed."""
    def __init__(self, models_dir: str = "models", min_width: int = 80, min_sharpness: float = 60.0):
        root = Path(models_dir)
        self.detector_path = root / "face_detection_yunet_2023mar.onnx"
        self.recognizer_path = root / "face_recognition_sface_2021dec.onnx"
        self.min_width = min_width
        self.min_sharpness = min_sharpness
        self._detector = None
        self._recognizer = None

    @property
    def available(self) -> bool:
        return self.detector_path.is_file() and self.recognizer_path.is_file()

    def _load(self, width: int, height: int):
        if not self.available:
            raise RuntimeError("FACE_MODEL_MISSING")
        if self._detector is None:
            self._detector = cv2.FaceDetectorYN.create(str(self.detector_path), "", (width, height), 0.9, 0.3, 5000)
            self._recognizer = cv2.FaceRecognizerSF.create(str(self.recognizer_path), "")
        self._detector.setInputSize((width, height))

    def inspect(self, image_bytes: bytes) -> FaceCheck:
        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return FaceCheck(False, "INVALID_IMAGE")
        height, width = image.shape[:2]
        try:
            self._load(width, height)
        except (RuntimeError, cv2.error):
            return FaceCheck(False, "MODEL_UNAVAILABLE")
        sharpness = float(cv2.Laplacian(image, cv2.CV_64F).var())
        _, faces = self._detector.detect(image)
        if faces is None or len(faces) == 0:
            return FaceCheck(False, "NO_FACE_DETECTED")
        if len(faces) != 1:
            return FaceCheck(False, "MULTIPLE_FACES")
        face = faces[0]
        if float(face[2]) < self.min_width:
            return FaceCheck(False, "FACE_TOO_SMALL")
        if sharpness < self.min_sharpness:
            return FaceCheck(False, "IMAGE_TOO_BLURRY", quality_score=sharpness)
        aligned = self._recognizer.alignCrop(image, face)
        embedding = self._recognizer.feature(aligned).reshape(-1).astype(np.float32)
        return FaceCheck(True, "FACE_QUALITY_OK", embedding, sharpness)

    @staticmethod
    def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
        a = left.astype(np.float32).reshape(-1)
        b = right.astype(np.float32).reshape(-1)
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        return float(np.dot(a, b) / denom) if denom else -1.0
