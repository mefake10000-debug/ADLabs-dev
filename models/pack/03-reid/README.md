# 03-reid

Appearance embeddings to associate identities ACROSS cameras within a session. No storage-day identity claims.

| weight | size | license | priority | source URL(s) | purpose |
|---|---|---|---|---|---|
| `osnet_x0_25_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth` | ~8.9MB | MIT | P0 | https://huggingface.co/kaiyangzhou/osnet/resolve/main/osnet_x0_25_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth | OSNet x0.25 (MSMT17 combine-all) - CPU edge embedding for session-scoped cross-cam association. |
| `osnet_x1_0_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth` | ~16.5MB | MIT | P1 | https://huggingface.co/kaiyangzhou/osnet/resolve/main/osnet_x1_0_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth | OSNet x1.0 (same recipe) - higher embedding quality for offline audits. |
| `osnet_x0_25_msmt17.onnx` | ~885.9KB | MIT (unofficial ONNX conversion) | P2 | https://huggingface.co/anriha/osnet_x0_25_msmt17/resolve/main/osnet_x0_25_msmt17.onnx | Third-party ONNX export of OSNet x0.25 - CPU inference without torchreid. Verify accuracy vs .pth. |
| `person_reid_youtu_2021nov.onnx` | ~101.9MB | Apache-2.0 | P2 | https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/person_reid_youtureid/person_reid_youtu_2021nov.onnx | OpenCV Zoo YouTu person ReID (ONNX/OpenCV-DNN, CPU-friendly) as a torch-free fallback embedder. |
| `person_reid_youtu_2021nov.onnx` | ~101.9MB | Apache-2.0 | P2 | https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/person_reid_youtureid/person_reid_youtu_2021nov.onnx | OpenCV Zoo YouTu person ReID (ONNX/OpenCV-DNN, CPU-friendly) as a torch-free fallback embedder. |

```python
import torchreid; m=torchreid.models.build_model('osnet_x1_0', use_gpu=False); torchreid.utils.load_pretrained_weights(m, path); emb=m(crops)  # (N,512)
```
