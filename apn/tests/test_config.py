import unittest
from pathlib import Path

from apn.config import load_config


class ConfigTests(unittest.TestCase):
    def test_phase_zero_camera_config_validates(self):
        config = load_config(Path(__file__).parents[1] / "config" / "cameras.yaml")
        self.assertEqual(config.mode, "COMPOSED")
        self.assertEqual(
            [camera.id for camera in config.cameras],
            ["CAM-01", "CAM-02", "CAM-03", "CAM-04"],
        )
        self.assertEqual(
            [camera.clock_offset_s for camera in config.cameras],
            [0.0, 15.0, 18.958, 21.958],
        )


if __name__ == "__main__":
    unittest.main()
