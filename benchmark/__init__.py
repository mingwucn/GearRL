"""Versioned benchmark generation for certified GearRL experiments."""

from .generator import BenchmarkGenerator, BenchmarkInstance
from .curated import (
    CuratedBenchmarkFreezer,
    CuratedBenchmarkLoader,
    CuratedCaseCatalog,
    CuratedRequirementsFirstFactory,
    FrozenCuratedDataset,
    SolverInputDirectoryLoader,
)
from .oracle import (
    ExactCompoundTrainOracle,
    GroundTruthOracle,
    OracleProof,
    OracleResult,
    ReplayableExactCompoundTrainOracle,
    ReplayableOracleProofVerifier,
)
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
    "SolverInputDirectoryLoader",
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
    "ReplayableExactCompoundTrainOracle",
    "ReplayableOracleProofVerifier",
    "PrescribedShaft",
    "ProblemSpecification",
    "RequirementsFirstBenchmarkCase",
    "SolverBenchmarkView",
    "SolverPayloadGuard",
]
