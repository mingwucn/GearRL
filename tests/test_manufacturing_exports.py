from benchmark.generator import BenchmarkGenerator
from manufacturing.exporters import ManufacturingExporter


def test_svg_and_dxf_exports_capture_all_certified_stages(tmp_path) -> None:
    train = BenchmarkGenerator().generate_compound_instances(3, 1)[0].reference_train
    exporter = ManufacturingExporter()
    svg = exporter.export_svg(train, tmp_path / "layout.svg")
    dxf = exporter.export_dxf(train, tmp_path / "layout.dxf")
    assert svg.exists() and "<circle" in svg.read_text()
    assert dxf.exists() and dxf.read_text().count("CIRCLE") == 2 * sum(len(stage.teeth) for stage in train.stages)
