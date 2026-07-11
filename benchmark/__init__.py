"""Versioned benchmark generation for certified GearRL experiments."""

from .generator import BenchmarkGenerator, BenchmarkInstance
from .curated import (
    CuratedBenchmarkFreezer,
    CuratedBenchmarkLoader,
    CuratedCaseCatalog,
    CuratedRequirementsFirstFactory,
    FrozenCuratedDataset,
)
from .oracle import ExactCompoundTrainOracle, GroundTruthOracle, OracleProof, OracleResult
from .specification import (
    DesignSpace,
    GroundTruthEvidence,
    PrescribedShaft,
    ProblemSpecification,
    RequirementsFirstBenchmarkCase,
    SolverBenchmarkView,
    SolverPayloadGuard,
)
from .freeze import BenchmarkFreezer
from .external import ExternalBenchmarkRegistry, ExternalCaseMetadata
from .protocol import BenchmarkProtocol, FrozenBenchmarkFactory
from .loader import FrozenBenchmarkLoader

__all__ = [
    "BenchmarkFreezer",
    "BenchmarkGenerator",
    "BenchmarkInstance",
    "BenchmarkProtocol",
    "CuratedBenchmarkFreezer",
    "CuratedBenchmarkLoader",
    "CuratedCaseCatalog",
    "CuratedRequirementsFirstFactory",
    "FrozenCuratedDataset",
    "DesignSpace",
    "ExternalBenchmarkRegistry",
    "ExternalCaseMetadata",
    "FrozenBenchmarkFactory",
    "FrozenBenchmarkLoader",
    "GroundTruthEvidence",
    "GroundTruthOracle",
    "ExactCompoundTrainOracle",
    "OracleProof",
    "OracleResult",
    "PrescribedShaft",
    "ProblemSpecification",
    "RequirementsFirstBenchmarkCase",
    "SolverBenchmarkView",
    "SolverPayloadGuard",
]
