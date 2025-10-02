# -*- coding: utf-8 -*-
# tests/test_image_utils.py
import unittest
import sys
import os
import tempfile
from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from image_utils import get_image_info, scan_images, validate_image_pairs


class TestImageUtils(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.create_test_images()

    def create_test_images(self):
        self.front_files = []
        self.back_files = []

        for i in range(3):
            # Front images
            front_path = os.path.join(self.temp_dir, f'front_{i}.png')
            img = Image.new('RGB', (90, 50), color=(i * 50, 100, 200))
            img.save(front_path)
            self.front_files.append(front_path)

            # Back images
            back_path = os.path.join(self.temp_dir, f'back_{i}.png')
            img = Image.new('RGB', (90, 50), color=(200, 100, i * 50))
            img.save(back_path)
            self.back_files.append(back_path)

    def test_get_image_info(self):
        info = get_image_info(self.front_files[0])
        self.assertEqual(info['size'], (90, 50))
        self.assertEqual(info['filename'], 'front_0.png')

    def test_scan_images(self):
        infos, errors = scan_images(self.front_files)
        self.assertEqual(len(infos), 3)
        self.assertEqual(len(errors), 0)

    def test_validate_pairs(self):
        front_infos = [get_image_info(f) for f in self.front_files]
        back_infos = [get_image_info(f) for f in self.back_files]

        errors, warnings = validate_image_pairs(front_infos, back_infos, '1:1')
        self.assertEqual(len(errors), 0)


if __name__ == '__main__':
    unittest.main()