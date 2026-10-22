# OSNet-x0.5 MSMT17 (soft ReID)

| | |
|--|--|
| **File** | `osnet_x0_5_msmt17.pth` (~11MB) |
| **Source** | [kaiyangzhou/osnet on Hugging Face](https://huggingface.co/kaiyangzhou/osnet) |
| **Role** | Stronger edge-viable body ReID than x0.25 (~0.6M params, 0.27 GFLOPs) |
| **Wired?** | **No** — `models.reid.enabled: false` by default. Cross-cam fusion not shipped. |
| **Privacy** | Body appearance only. No face ReID. Day-local gallery. Never CRM identity. |

Prefer this weight when Mac mini / GPU headroom allows; keep x0.25 as default path in `pipeline.yaml`.
