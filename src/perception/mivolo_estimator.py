"""MiVOLO v2 local inference; only cohort aggregates leave the pipeline."""
from pathlib import Path
import numpy as np
from src.perception.age_gender import band_for_age


def prepare_crop(crop):
    import cv2
    if crop is None or not getattr(crop, 'size', 0):
        return np.zeros((3,384,384),dtype=np.float32)
    rgb=cv2.cvtColor(cv2.resize(crop,(384,384)),cv2.COLOR_BGR2RGB).astype(np.float32)/255
    rgb=(rgb-np.array([.485,.456,.406],dtype=np.float32))/np.array([.229,.224,.225],dtype=np.float32)
    return rgb.transpose(2,0,1)


def decode_prediction(row):
    logits=np.asarray(row[:2],dtype=np.float64)
    probs=np.exp(logits-logits.max()); probs/=probs.sum()
    age=int(round(float(np.clip(float(row[2])*122+61,0,120))))
    return dict(age=age,age_band=band_for_age(age),gender='female' if probs[1]>=.5 else 'male',gender_confidence=round(float(probs.max()),3),p_female=round(float(probs[1]),4),p_male=round(float(probs[0]),4))


class MiVoloEstimator:
    def __init__(self, directory):
        import torch
        from mivolo.model.mivolo_model import mivolo_d1_384
        from safetensors.torch import load_file
        self.model=mivolo_d1_384(pretrained=False,num_classes=3,in_chans=6)
        state=load_file(str(Path(directory)/'model.safetensors'))
        state={key.removeprefix('mivolo.model.'):value for key,value in state.items()}
        self.model.load_state_dict(state,strict=True)
        self.model.eval()
        self.calls=0

    def predict_batch(self, crops, bodies=None):
        import torch
        if not crops:
            return []
        bodies=bodies if bodies is not None else [None]*len(crops)
        inputs=np.stack([np.concatenate([prepare_crop(face),prepare_crop(body)]) for face,body in zip(crops,bodies)])
        with torch.inference_mode():
            rows=self.model(torch.from_numpy(inputs)).cpu().numpy()
        self.calls+=1
        return [decode_prediction(row) for row in rows]
