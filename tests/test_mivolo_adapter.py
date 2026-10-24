import unittest
import numpy as np
from src.perception.mivolo_estimator import decode_prediction, prepare_crop

class MiVoloAdapterTests(unittest.TestCase):
    def test_bgr_is_resized_and_normalized_as_rgb(self):
        image=np.zeros((20,30,3),dtype=np.uint8); image[:,:,2]=255
        result=prepare_crop(image)
        self.assertEqual(result.shape,(3,384,384))
        self.assertAlmostEqual(float(result[0,0,0]),(1-.485)/.229,places=4)
        self.assertAlmostEqual(float(result[2,0,0]),-.406/.225,places=4)

    def test_age_regression_and_gender_softmax(self):
        result=decode_prediction([0,2,0])
        self.assertEqual(result['age'],61)
        self.assertEqual(result['gender'],'female')
        self.assertAlmostEqual(result['p_female'],.8808,places=4)
