import unittest
from apn.perception.floor import FloorProjection


class FloorProjectionTests(unittest.TestCase):
    def test_exact_square_projection_has_near_zero_residual(self):
        projection, residual = FloorProjection.fit(
            [[0,0],[100,0],[100,100],[0,100]], [[10,20],[20,20],[20,30],[10,30]])
        self.assertLess(residual, 1e-4)
        x, y = projection.project((50, 50))
        self.assertAlmostEqual(x, 15, places=4)
        self.assertAlmostEqual(y, 25, places=4)

    def test_uncalibrated_projection_is_normalised_and_labelled_approximate(self):
        projection = FloorProjection(None)
        self.assertTrue(projection.approximate)
        self.assertEqual(projection.project((640, 360), (1280, 720)), (.5, .5))


if __name__ == "__main__": unittest.main()
