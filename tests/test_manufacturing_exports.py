from benchmark.generator import generate_compound_instances
from manufacturing.exporters import export_dxf, export_svg


def test_svg_and_dxf_exports_capture_all_certified_stages(tmp_path) -> None:
    train = generate_compound_instances(3, 1)[0].reference_train
    svg = export_svg(train, tmp_path / "layout.svg")
    dxf = export_dxf(train, tmp_path / "layout.dxf")
    assert svg.exists() and "<circle" in svg.read_text()
    assert dxf.exists() and dxf.read_text().count("CIRCLE") == 2 * sum(len(stage.teeth) for stage in train.stages)
