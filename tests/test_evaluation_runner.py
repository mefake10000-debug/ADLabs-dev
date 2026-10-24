import unittest

class EvaluationRunnerTests(unittest.TestCase):
    def test_counts_false_positives_misses_and_empty_frames(self):
        from src.evaluation import evaluate_frames
        labels = [{'frame_id': '1', 'boxes': [[0, 0, 10, 10], [20, 20, 30, 30]]}, {'frame_id': '2', 'boxes': []}]
        predictions = [{'frame_id': '1', 'boxes': [[0, 0, 10, 10]]}, {'frame_id': '2', 'boxes': [[0, 0, 10, 10]]}]
        result = evaluate_frames(labels, predictions)
        self.assertEqual(result['metrics'], {'precision': 0.5, 'recall': 0.5, 'f1': 0.5, 'count_mae': 1.0})
        self.assertEqual(result['ground_truth_people'], 2)

    def test_duplicate_predictions_do_not_match_one_person_twice(self):
        from src.evaluation import evaluate_frames
        labels = [{'frame_id': '1', 'boxes': [[0, 0, 10, 10]]}]
        predictions = [{'frame_id': '1', 'boxes': [[0, 0, 10, 10], [0, 0, 10, 10]]}]
        self.assertEqual(evaluate_frames(labels, predictions)['metrics']['precision'], 0.5)

    def test_missing_frames_duplicates_and_invalid_boxes_are_rejected(self):
        from src.evaluation import evaluate_frames
        good = [{'frame_id': '1', 'boxes': [[0, 0, 10, 10]]}]
        for bad in ([], good + good, [{'frame_id': '1', 'boxes': [[0, 0, float('nan'), 10]]}]):
            with self.assertRaises(ValueError):
                evaluate_frames(good, bad)
