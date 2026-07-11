from dataclasses import replace

from benchmark.specification import DesignSpace, PrescribedShaft, ProblemSpecification
from common.certificate_binding import ValidationCertificateBinder
from common.design_models import DesignConstraints, DesignProblem, GearStage, GearTrain, MeshEdge, Point2D
from physics_validator.reference_verifier import ReferenceVerifier
from synthesis.requirements_solver import ProductionCandidateValidator


def _subjects() -> tuple[ProblemSpecification, GearTrain]:
    problem = DesignProblem(
        (Point2D(-50, -50), Point2D(100, -50), Point2D(100, 50), Point2D(-50, 50)),
        "input",
        "output",
        DesignConstraints(target_speed_ratio=1.0, min_teeth=20, max_teeth=20),
    )
    train = GearTrain(
        (
            GearStage("input", Point2D(0, 0), (20,), 1.0, (0,)),
            GearStage("idler", Point2D(20, 0), (20, 20), 1.0, (0, 1)),
            GearStage("output", Point2D(40, 0), (20,), 1.0, (1,)),
        ),
        (MeshEdge("input", 0, "idler", 0), MeshEdge("idler", 1, "output", 0)),
    )
    specification = ProblemSpecification(
        "requirements-first-v1",
        problem,
        DesignSpace((1.0,), 3, 3),
        (PrescribedShaft("input", Point2D(0, 0)), PrescribedShaft("output", Point2D(40, 0))),
    )
    return specification, train


def test_reference_certificate_is_bound_to_exact_problem_and_train() -> None:
    specification, train = _subjects()
    certificate = ReferenceVerifier.verify(specification.problem, train)
    binder = ValidationCertificateBinder()

    assert binder.matches(certificate, specification.problem, train)
    changed_train = replace(train, stages=(*train.stages[:-1], replace(train.stages[-1], teeth=(19,))))
    assert not binder.matches(certificate, specification.problem, changed_train)


def test_production_certificate_binds_full_specification() -> None:
    specification, train = _subjects()
    certificate = ProductionCandidateValidator().validate(specification, train)

    assert certificate.valid
    assert certificate.subject_identity is not None
    assert certificate.subject_identity.subject_schema == "requirements-first-v1"
    assert ValidationCertificateBinder().matches(certificate, specification, train)
