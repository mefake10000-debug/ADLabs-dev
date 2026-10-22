# 04-face-attr

Face PROCESSING for privacy workflows (redaction) and consented staff features. No identity of shoppers.

| weight | size | license | priority | source URL(s) | purpose |
|---|---|---|---|---|---|
| `face_detection_yunet_2023mar.onnx` | ~227.1KB | Apache-2.0 | P0 | https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx | YuNet face detector - blur/redact boxes, face-crop gating for attribute estimates, NOT identity. |
| `facial_expression_recognition_mobilefacenet_2022july.onnx` | ~4.6MB | Apache-2.0 | P2 | https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/facial_expression_recognition/facial_expression_recognition_mobilefacenet_2022july.onnx | Zoo expression classifier - aggregate-only crowd engagement trend. Never per-person truth. |
| `face_recognition_sface_2021dec.onnx` | ~36.9MB | Apache-2.0 | P2 | https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx | SFace 128-d embedding - ONLY for staff shift-login with explicit consent + template governance. |
| `buffalo_l.zip` | ~275.3MB | NON-COMMERCIAL research (insightface python-package license) | P2-research | https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip | Optional age/gender+ArcFace pack. Legal review required before any commercial deployment. |
