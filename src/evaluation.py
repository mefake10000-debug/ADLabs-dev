"""Offline person-box evaluation. Labels must come from independently reviewed footage.

python -m src.evaluation --labels labels.json --predictions predictions.json \
  --model MODEL --clip CLIP --config-id CONFIG --dataset NAME --output report.json
Input: {"frames": [{"frame_id": "001", "boxes": [[x1,y1,x2,y2]]}]}.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def _frames(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('A non-empty frame list is required')
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('frame_id'), str) or not row['frame_id']:
            raise ValueError('Every frame needs a non-empty string frame_id')
        key, boxes = row['frame_id'], row.get('boxes')
        if key in result or not isinstance(boxes, list) or len(boxes) > 500:
            raise ValueError('Duplicate frame ID or invalid box list (maximum 500 boxes/frame)')
        for box in boxes:
            if not isinstance(box, list) or len(box) != 4 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in box):
                raise ValueError('Boxes must contain four finite coordinates')
            if box[2] <= box[0] or box[3] <= box[1]:
                raise ValueError('Boxes must have positive area')
        result[key] = boxes
    return result


def _iou(a, b):
    area = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return area / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - area)


def evaluate_frames(labels, predictions, *, iou_threshold=0.5):
    if not 0 < iou_threshold <= 1:
        raise ValueError('IoU threshold must be in (0,1]')
    truth, predicted = _frames(labels), _frames(predictions)
    if truth.keys() != predicted.keys():
        raise ValueError('Labels and predictions must cover exactly the same frames, including empty frames')
    tp = fp = fn = error = total_people = 0
    for key, boxes in truth.items():
        detections = predicted[key]
        # Maximum-cardinality one-to-one matching avoids assigning two boxes to one person.
        edges = [[j for j, target in enumerate(boxes) if _iou(box, target) >= iou_threshold] for box in detections]
        matched = {}
        def assign(index, seen):
            for target in edges[index]:
                if target in seen:
                    continue
                seen.add(target)
                if target not in matched or assign(matched[target], seen):
                    matched[target] = index
                    return True
            return False
        count = sum(assign(index, set()) for index in range(len(detections)))
        tp += count
        fp += len(detections) - count
        fn += len(boxes) - count
        error += abs(len(detections) - len(boxes))
        total_people += len(boxes)
    if not total_people:
        raise ValueError('Include labeled people as well as empty frames')
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn)
    return {'labeled_frames': len(truth), 'ground_truth_people': total_people,
            'metrics': {'precision': precision, 'recall': recall,
                        'f1': 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
                        'count_mae': error / len(truth)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('labels', 'predictions', 'model', 'clip', 'config-id', 'dataset', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    labels_bytes, prediction_bytes = Path(args.labels).read_bytes(), Path(args.predictions).read_bytes()
    result = evaluate_frames(json.loads(labels_bytes)['frames'], json.loads(prediction_bytes)['frames'])
    report = {'schema_version': 1, 'evaluated_at': datetime.now(timezone.utc).isoformat(),
              'model': args.model, 'clip': args.clip, 'config_id': args.config_id,
              'dataset': {'name': args.dataset, 'labeled_frames': result['labeled_frames'], 'ground_truth_people': result['ground_truth_people']},
              'metrics': result['metrics'], 'iou_threshold': 0.5,
              'labels_sha256': hashlib.sha256(labels_bytes).hexdigest(),
              'predictions_sha256': hashlib.sha256(prediction_bytes).hexdigest()}
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + '.tmp')
    temporary.write_text(json.dumps(report, indent=2) + '\n')
    temporary.replace(target)


if __name__ == '__main__':
    main()
