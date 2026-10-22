# 05-open-vocab/clip-vit-base-patch32

Text-prompted detection (YOLO-World) + CLIP for zero-shot classification of products/contexts.

| weight | size | license | priority | source URL(s) | purpose |
|---|---|---|---|---|---|
| `config.json` | ~4.1KB | MIT | P0 | https://huggingface.co/openai/clip-vit-base-patch32/resolve/main/config.json | CLIP ViT-B/32 config. |
| `preprocessor_config.json` | ~316.0B | MIT | P0 | https://huggingface.co/openai/clip-vit-base-patch32/resolve/main/preprocessor_config.json | CLIP preprocessor (CLIPImageProcessor). |
| `tokenizer.json` | ~2.1MB | MIT | P0 | https://huggingface.co/openai/clip-vit-base-patch32/resolve/main/tokenizer.json | Fast tokenizer for text-prompt embedding. |
| `tokenizer_config.json` | ~592.0B | MIT | P0 | https://huggingface.co/openai/clip-vit-base-patch32/resolve/main/tokenizer_config.json | Tokenizer config. |
| `vocab.json` | ~842.1KB | MIT | P0 | https://huggingface.co/openai/clip-vit-base-patch32/resolve/main/vocab.json | BPE vocab. |
| `merges.txt` | ~512.4KB | MIT | P0 | https://huggingface.co/openai/clip-vit-base-patch32/resolve/main/merges.txt | BPE merges. |
| `special_tokens_map.json` | ~389.0B | MIT | P0 | https://huggingface.co/openai/clip-vit-base-patch32/resolve/main/special_tokens_map.json | Special tokens. |
| `pytorch_model.bin` | ~577.2MB | MIT | P0 | https://huggingface.co/openai/clip-vit-base-patch32/resolve/main/pytorch_model.bin | CLIP ViT-B/32 weights (fp32, 605 MB) - zero-shot shelf-looks, prompt emb. for YOLO-World. |

```python
from ultralytics import YOLOWorld; YOLOWorld('models/pack/05-open-vocab/yolov8s-worldv2.pt').set_classes([...])
```
