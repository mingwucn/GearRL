import json

import cv2
import numpy as np

from preprocessing.processor import Processor


def test_preprocessor_emits_normalized_geometry_from_a_fixture_image(tmp_path):
    image = np.zeros((120, 120, 3), dtype=np.uint8)
    cv2.rectangle(image, (5, 5), (115, 115), (255, 255, 255), 2)
    cv2.circle(image, (25, 60), 5, (0, 0, 255), -1)
    cv2.circle(image, (95, 60), 5, (0, 255, 0), -1)
    image_path = tmp_path / "fixture.png"
    constraints_path = tmp_path / "constraints.json"
    output_path = tmp_path / "processed.json"
    assert cv2.imwrite(str(image_path), image)
    constraints_path.write_text(json.dumps({"torque_ratio": "free"}))

    constraints = Processor.process_input(image_path, constraints_path, output_path)
    data = json.loads(output_path.read_text())

    assert constraints["torque_ratio"] == "free"
    assert data["normalized_space"]["input_shaft"] is not None
    assert data["normalized_space"]["output_shaft"] is not None
    assert len(data["normalized_space"]["boundaries"]) >= 3
