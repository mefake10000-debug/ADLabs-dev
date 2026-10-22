import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Input geometry and normalisation come from the model's own preprocessor_config.json
# (ViTFeatureExtractor): 224x224, rescale 1/255, ImageNet mean/std, RGB order.
INPUT_SIZE = 224
RESCALE = 1.0 / 255.0
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)

# Age bands used for cohort reporting. Coarse on purpose: finer bands would produce
# cohorts too small to be statistically meaningful and too close to an identifier.
AGE_BANDS = [
    (0, 17, "under_18"),
    (18, 24, "18_24"),
    (25, 34, "25_34"),
    (35, 44, "35_44"),
    (45, 54, "45_54"),
    (55, 120, "55_plus"),
]


class AgeGenderEstimator:
    """Estimates an age band and gender cohort for a detected face.

    Model: `abhilash88/age-gender-prediction`, a ViT-Base dual-head network trained on
    UTKFace (94.3% gender accuracy, 4.5-year age MAE), exported to ONNX by
    `onnx-community`. It runs through onnxruntime, which on Apple Silicon can use the
    CoreML execution provider.

    PRIVACY CONTRACT -- this class deliberately produces *cohorts*, not identities:
      * the face crop exists only for the duration of the inference call and is never
        written to disk, logged, or transmitted;
      * the model has no identity head, so it cannot recognise anyone -- it only
        predicts an age and a gender from pixels;
      * downstream, a cohort is only surfaced once it reaches the k-anonymity threshold
        (see src/analytics/demographics.py), so a single inferred person is never
        reportable on its own;
      * nothing is joined to a person across sessions: the cohort is attached to an
        ephemeral in-memory track id that is discarded when the track ends.
    """

    def __init__(
        self,
        session: Any,
        input_name: str = "pixel_values",
        output_name: str = "logits",
        age_scale: float = 1.0,
        min_face_px: float = 32.0,
    ):
        self.session = session
        self.input_name = input_name
        self.output_name = output_name
        # The model's age head is a direct regression on years; age_scale stays a
        # knob so a differently-normalised export can be corrected without a code
        # change (verified empirically against the reference checkpoint).
        self.age_scale = age_scale
        self.min_face_px = min_face_px

    def predict_batch(self, crops: List[Any]) -> List[Dict[str, Any]]:
        """Runs the model on a batch of BGR face crops. Returns one result per crop."""
        if not crops:
            return []
        import cv2
        import numpy as np

        batch = np.empty((len(crops), 3, INPUT_SIZE, INPUT_SIZE), dtype=np.float32)
        for i, crop in enumerate(crops):
            if crop is None or getattr(crop, "size", 0) == 0:
                batch[i] = 0.0
                continue
            resized = cv2.resize(crop, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_LINEAR)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) * RESCALE
            rgb = (rgb - np.array(MEAN, dtype=np.float32)) / np.array(STD, dtype=np.float32)
            batch[i] = rgb.transpose(2, 0, 1)

        try:
            outputs = self.session.run([self.output_name], {self.input_name: batch})
            logits = outputs[0]
        except Exception as e:
            logger.error(f"Age/gender inference error: {e}")
            return []

        results = []
        for row in logits:
            age_raw = float(row[0]) * self.age_scale
            age = int(round(age_raw))
            age = max(0, min(120, age))
            p_female = float(row[1])
            gender = "female" if p_female >= 0.5 else "male"
            confidence = max(p_female, 1.0 - p_female)
            results.append({
                "age": age,
                "age_band": band_for_age(age),
                "gender": gender,
                "gender_confidence": round(confidence, 3),
                "p_female": round(p_female, 4),
                "p_male": round(1.0 - p_female, 4),
            })
        return results


def band_for_age(age: int) -> str:
    for lo, hi, name in AGE_BANDS:
        if lo <= age <= hi:
            return name
    return "unknown"
