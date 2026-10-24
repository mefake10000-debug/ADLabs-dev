# LocateAnything-3B — EdgeSight integration brief

**Status for ADLabs retail CCTV:** **FUTURE** (research / gated eval only).  
**Do not download into the default pack now** — NVIDIA non-commercial license + ~7.8 GB weights + CUDA-oriented VLM runtime make it unfit for the LIVE `EDGE_PERF_MODE=fast` path.

---

## 1. What it is (honest)

| Field | Fact |
|--------|------|
| Exact HF id | [`nvidia/LocateAnything-3B`](https://huggingface.co/nvidia/LocateAnything-3B) |
| Org | NVIDIA (Eagle / Embodied line; LPR lab) |
| Paper | [LocateAnything: Fast and High-Quality Vision-Language Grounding with Parallel Box Decoding](https://arxiv.org/abs/2605.27365) · arXiv:2605.27365 |
| Authors | Shihao Wang, Shilong Liu, Yuanguo Kuang, Xinyu Wei, Yangzhou Liu, Zhiqi Li, Yunze Man, Guo Chen, Andrew Tao, Guilin Liu, Jan Kautz, Lei Zhang, Zhiding Yu |
| Project page | https://research.nvidia.com/labs/lpr/locate-anything/ |
| Code | https://github.com/NVlabs/Eagle/tree/main/Embodied |
| Demo | https://huggingface.co/spaces/nvidia/LocateAnything |
| PDF | https://research.nvidia.com/labs/lpr/locate-anything/LocateAnything.pdf |
| Parameter count | ~**3.83B** BF16 params (HF safetensors); marketed as **LocateAnything-3B** / “3B” / “Model size 4B params” |
| Architecture | **Vision–language grounding VLM** (not a YOLO detector): MoonViT vision encoder + MLP projector + **Qwen2.5-3B-Instruct** LM; **Parallel Box Decoding (PBD)** emits full boxes/points as atomic blocks |
| Role | Open-vocab / open-world **localization & grounding**: detect, referring-expression ground, multi-object dense boxes, GUI/text/layout, point localization |
| Ultralytics? | **No** — Hugging Face `transformers` + `trust_remote_code=True` |

It is **not** a drop-in replacement for YOLO26/11, YOLO-World, or YOLOE. It is a heavier generalist grounding VLM that answers free-form “where is X?” with structured box/point tokens. Official card lists **industrial inspection / surveillance** among intended research use cases, but the **license blocks commercial store deployment** without NVIDIA commercial rights.

---

## 2. License (blocker)

- Card: `license: other` / `license_name: nvidia-license`  
  https://huggingface.co/nvidia/LocateAnything-3B/blob/main/LICENSE
- **Non-commercial only** — research / evaluation. Commercial use **not permitted** except NVIDIA and affiliates.
- Components: Qwen2.5-3B-Instruct (**Qwen Research License**), MoonViT-SO-400M (**MIT**).
- Same gating posture as pack `buffalo_l` / insightface: **do not** put in default `scripts/download/download_pack_models.py` without an explicit `--include-research` + legal note.

**Recommendation:** keep YOLO-World / YOLOE / CLIP as production open-vocab; treat LocateAnything as **on-demand research** if/when a commercial license or NVIDIA product path exists.

---

## 3. Inputs / outputs

**Inputs**

- RGB image (native resolution; production claims up to ~2.5K)
- Natural-language text (categories, referring phrases, GUI/OCR/point prompts)

**Outputs**

- Generated text with structured coordinate tokens:
  - Boxes: `<box><x1><y1><x2><y2></box>` — coords normalized integers in **[0, 1000]**
  - Points: shorter `<box><x><y></box>` form
- Multi-object: yes (`ground_multi`, category lists joined with `</c>`)
- Modes: `fast` (MTP only), `slow` (autoregressive), `hybrid` (default — MTP + AR fallback)

Not masks by default (boxes/points). No Ultralytics-style `.boxes` tensor without a parser.

---

## 4. Weights, size, hardware

| Item | Value |
|------|--------|
| HF repo | `nvidia/LocateAnything-3B` |
| Shards | `model-00001-of-00002.safetensors` + `model-00002-of-00002.safetensors` |
| Approx disk | **~7.8 GB** (`usedStorage` ≈ 7.79e9 bytes) + tokenizer/code |
| Official runtime | **Transformers**, BF16, KV cache; **Linux + NVIDIA CUDA** (Ampere / Hopper / Blackwell / Lovelace). TensorRT / Triton **not** yet supported |
| Official test HW | H100 & A100 |
| VRAM (official probe) | A100, 4K image, batch 4, hybrid: **`la_flash` ~11.7 GB** peak reserved vs dense SDPA **~35 GB** |
| Third-party BF16 fit estimates | ~8–9 GB weights+overhead for short context (community; verify on target GPU) |
| Apple Silicon / MPS | **Not listed** as supported. Possible only via experimental PyTorch MPS / CPU — expect slow, unsupported, and out of EdgeSight Docker CPU fast path |
| CPU | Possible in theory; **not** feasible for interactive CCTV; multi-second+ per query |

**Disk on this machine:** ~59 GiB free — enough to download once, but **default pack should stay lean**; prefer on-demand / research flag.

---

## 5. Inference APIs

### Primary (official)

```python
from transformers import AutoModel, AutoProcessor, AutoTokenizer
# trust_remote_code required — custom LocateAnythingForConditionalGeneration

model = AutoModel.from_pretrained(
    "nvidia/LocateAnything-3B",  # or local dir
    torch_dtype=torch.bfloat16,
    trust_remote_code=True,
).to("cuda").eval()
processor = AutoProcessor.from_pretrained(..., trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained(..., trust_remote_code=True)
# model.generate(..., generation_mode="hybrid", max_new_tokens=8192)
```

Pinned install tip from model card:

```bash
pip install opencv-python-headless==4.11.0.86 transformers==4.57.1 \
  numpy==1.25.0 Pillow==11.1.0 peft torchvision decord==0.6.0 lmdb==1.7.5
# install torch for your CUDA separately
```

Optional: MagiAttention (Hopper/Blackwell) for faster MTP; else SDPA fallback. Batch path: `batch_infer.py` + `la_flash` attention from the HF repo / Eagle Embodied tree.

### Not available

- **Ultralytics** — no `YOLO("LocateAnything")`
- EdgeSight’s current `WorldDetector` (YOLO-World / YOLOE) — different stack

### Official worker sketch

NVIDIA ships a `LocateAnythingWorker` with `detect`, `ground_single`, `ground_multi`, `ground_text`, `detect_text`, `ground_gui`, `point`, plus `parse_boxes` / `parse_points`. Prefer that pattern over inventing prompts.

---

## 6. Retail CCTV comparison (vs stack we already have)

| Capability | YOLO-World + CLIP | YOLOE (prompt-free) | LocateAnything-3B |
|------------|-------------------|---------------------|-------------------|
| Live every-N-frame display interest | **Yes** (slow tier today) | **Yes** (shelf backend) | **No** — too heavy |
| Fixed retail category vocab | Strong | Built-in / filter | OK via `detect([...])` |
| Free phrase: “fire extinguisher by exit” | Weak / brittle | Weak | **Strong** (referring grounding) |
| Dense cluttered shelves | Decent boxes | Boxes + masks | Strong dense OD (research claims) |
| SKU barcode / POS SKU ID | **Out of scope** | Out of scope | Still **not** reliable SKU OCR from wide CCTV |
| Edge Mac/CPU Docker | Fits pack | Fits | CUDA research box |
| License for commercial demo | AGPL/MIT pack paths | AGPL | **NVIDIA non-commercial** |

**Where it would help EdgeSight (later):**

- Operator **“open-vocab locate”** search: type query → boxes on one snapshot
- Safety props (“locate fire extinguisher”, “AED”, “exit sign”) as **ops assist**, not certified fire-panel
- Ad-hoc display interest beyond fixed YOLO-World taxonomy

**Where it does not replace:**

- Person detect / track / ReID (YOLO26 + ByteTrack + OSNet)
- Face redaction (YuNet)
- Continuous shelf engagement KPI (keep YOLO-World / YOLOE)

---

## 7. Privacy / safety (store CCTV)

From NVIDIA ethical notes + ADLabs policy:

1. **License** — research/eval only until commercial rights exist.
2. **No blurring** — model does not anonymize people/PII/IP in inputs or outputs; operators must already own lawful CCTV rights.
3. **Do not** use for facial identity, multi-day shopper ReID, or “find this person” CRM — conflicts with EdgeSight DPDP posture (YuNet = redaction/gating only).
4. Prefer **object / fixture / safety-equipment** queries; avoid person-descriptive search in production UI.
5. Keep inference **on-prem**; do not send store frames to public Spaces demos.
6. Dashboard copy must stay honest: locate = **candidate boxes**, not certified safety detection or theft proof.

---

## 8. LIVE / PARTIAL / FUTURE

| Surface | Badge | Rationale |
|---------|--------|-----------|
| Dashboard continuous open-vocab products | **LIVE** today via YOLO-World / YOLOE | Already wired; keep |
| Dashboard “type any phrase → locate” | **FUTURE** | Needs CUDA worker + license + lazy load |
| Internal research notebook / gated `/api/v1/locate` behind flag | **PARTIAL** only if legal OK + weights present | Prototype; no accuracy claims |
| Default `EDGE_PERF_MODE=fast` every-frame | **Never** | Conflicts with FPS floor |

---

## 9. Recommended placement

```
repos/ADLabs-dev/models/pack/08-locateanything/   # research-gated; NOT in default download
  README.md          # license + purpose + non-commercial banner
  .gitignore         # ignore weights
  nvidia-LocateAnything-3B/   # huggingface-cli snapshot (optional)
# OR
repos/ADLabs-dev/weights/locateanything/nvidia-LocateAnything-3B/
```

Do **not** mix into `05-open-vocab` (YOLO-World/CLIP) — different runtime and license class. Mirror desktop pack only if research flag is on:

`~/Desktop/ad-labs-project/models/pack/08-locateanything/` (optional).

---

## 10. Download commands (on-demand; dry-run first)

**Prefer documenting + stub — do not auto-pull ~8 GB into CI/demo images.**

### huggingface-cli (recommended)

```bash
# Dry-run / inspect only
huggingface-cli download nvidia/LocateAnything-3B --dry-run

# On-demand research download (requires HF login if rate-limited)
export LOCATEANYTHING_DIR="${ADLABS_ROOT:-$HOME/Desktop/ad-labs-project/repos/ADLabs-dev}/models/pack/08-locateanything/nvidia-LocateAnything-3B"
mkdir -p "$(dirname "$LOCATEANYTHING_DIR")"
huggingface-cli download nvidia/LocateAnything-3B \
  --local-dir "$LOCATEANYTHING_DIR" \
  --local-dir-use-symlinks False
```

### wget (safetensors shards only — still need code/tokenizer files)

```bash
BASE=https://huggingface.co/nvidia/LocateAnything-3B/resolve/main
DEST=models/pack/08-locateanything/nvidia-LocateAnything-3B
mkdir -p "$DEST"
# Prefer `huggingface-cli download` for full snapshot (config + modeling_*.py + tokenizer).
# Example shard URLs if you must:
# wget -c "$BASE/model-00001-of-00002.safetensors" -O "$DEST/model-00001-of-00002.safetensors"
# wget -c "$BASE/model-00002-of-00002.safetensors" -O "$DEST/model-00002-of-00002.safetensors"
```

### Sibling to `scripts/download/download_pack_models.py` (pattern)

Extend with a **research-only** item gated like `buffalo_l`:

```python
# Pseudocode — do NOT enable in default ITEMS without --include-research
dict(
    key="nvidia-LocateAnything-3B",  # directory snapshot via hf CLI, not single URL
    folder="08-locateanything",
    size=7_789_000_000,  # approx; verify before pin
    research=True,
    license="NVIDIA License (non-commercial research/eval only)",
    prio="P3-research",
    purpose="VLM open-vocab locate / grounding — async ops search only; NOT every-frame.",
)
```

Dry-run stub idea: `scripts/download_locateanything_dryrun.py` prints dest path, license warning, `huggingface-cli download … --dry-run`, and exits 0 without writing weights.

---

## 11. Perf vs `EDGE_PERF_MODE=fast`

| Mode | LocateAnything |
|------|----------------|
| `fast` (person YOLO + ByteTrack only) | **Off**. Never load. |
| `quality` (pose / YuNet / World) | Still **off by default**. Optional separate process/GPU. |
| Operator locate query | **Async / on-demand**: grab latest frame for `cam_id`, run once, return boxes. Multi-second latency OK. |

Official H100 hybrid ~12.7 boxes/sec class throughput is **not** Mac Docker CPU. Treat as offline GPU sidecar.

---

## 12. Minimal FastAPI sketch (honest; no fake accuracy)

```python
# Sketch only — gate with LOCATEANYTHING_ENABLED=1 + research license ack.
# Do not claim IoU/F1 on retail CCTV without a store eval set.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import os

router = APIRouter(prefix="/api/v1", tags=["locate"])

class LocateRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=256)
    camera_id: str
    mode: str = "hybrid"  # fast | slow | hybrid
    max_boxes: int = Field(32, ge=1, le=128)

class LocateBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    label: Optional[str] = None  # only if parser extracts; else null

class LocateResponse(BaseModel):
    status: str  # "ok" | "disabled" | "unavailable"
    capability: str = "FUTURE"  # or PARTIAL when weights+CUDA ready
    camera_id: str
    query: str
    frame_ts_ms: Optional[int] = None
    boxes: list[LocateBox] = []
    raw_answer: Optional[str] = None
    note: str = (
        "Candidate open-vocab boxes from LocateAnything-3B; "
        "not certified safety detection; not POS SKU ID; "
        "NVIDIA non-commercial weights — research/eval only."
    )

@router.post("/locate", response_model=LocateResponse)
def locate(req: LocateRequest) -> LocateResponse:
    if os.environ.get("LOCATEANYTHING_ENABLED") != "1":
        return LocateResponse(
            status="disabled",
            capability="FUTURE",
            camera_id=req.camera_id,
            query=req.query,
            note="LocateAnything disabled. LIVE open-vocab remains YOLO-World/YOLOE products path.",
        )
    # 1) Fetch latest JPEG/ndarray for camera_id from analyzer ring buffer (no inventing frames).
    # 2) worker.ground_multi(image, req.query) or worker.detect(...)
    # 3) boxes = LocateAnythingWorker.parse_boxes(answer, w, h)[:req.max_boxes]
    # 4) Overlay on dashboard via existing debug overlay path — separate from person tracks.
    raise HTTPException(
        status_code=501,
        detail="LocateAnything worker not wired; see docs/models/locateanything-3b-integration.md",
    )
```

Dashboard: show **FUTURE** pill until `status==ok` and capability flips to PARTIAL; never invent boxes for demos.

---

## 13. Decision — download now?

| Choice | Verdict |
|--------|---------|
| Default pack / Docker demo | **No** |
| On-demand research GPU box | **Only** with legal ack + `--include-research`-style flag |
| Production commercial EdgeSight | **Blocked** until NVIDIA commercial license / alternate product |

**Keep:** YOLO-World + CLIP + YOLOE for LIVE open-vocab.  
**Defer:** LocateAnything weights and FastAPI worker until license + CUDA sidecar exist.

---

## Sources (official)

1. https://huggingface.co/nvidia/LocateAnything-3B  
2. https://huggingface.co/nvidia/LocateAnything-3B/blob/main/LICENSE  
3. https://github.com/NVlabs/Eagle/tree/main/Embodied  
4. https://research.nvidia.com/labs/lpr/locate-anything/  
5. https://arxiv.org/abs/2605.27365  
6. https://huggingface.co/spaces/nvidia/LocateAnything  
