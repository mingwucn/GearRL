"""Build a validated, editable Advanced Engineering Informatics package."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
from typing import Any

from reporting.manuscript import ManuscriptCitationResolver, ManuscriptClaimGuard


@dataclass(frozen=True)
class SubmissionConstraintResult:
    constraint_id: str
    passed: bool
    observed: Any
    limit: Any


class AEISubmissionValidator:
    """Apply the frozen journal constraints and expose unresolved author actions."""

    REQUIRED_METADATA = (
        "authors",
        "corresponding_author",
        "competing_interests_statement",
        "funding_statement",
        "archival_dataset_identifier",
    )

    def validate(self, manuscript: dict, submission: dict) -> dict[str, Any]:
        guide = submission["guide"]
        highlights = submission["highlights"]
        results = [
            SubmissionConstraintResult("abstract-word-limit", len(manuscript["abstract"].split()) <= guide["abstract_max_words"], len(manuscript["abstract"].split()), guide["abstract_max_words"]),
            SubmissionConstraintResult("keyword-count", guide["keyword_count_min"] <= len(manuscript["keywords"]) <= guide["keyword_count_max"], len(manuscript["keywords"]), [guide["keyword_count_min"], guide["keyword_count_max"]]),
            SubmissionConstraintResult("highlight-count", guide["highlight_count_min"] <= len(highlights) <= guide["highlight_count_max"], len(highlights), [guide["highlight_count_min"], guide["highlight_count_max"]]),
            SubmissionConstraintResult("highlight-length", all(len(item) <= guide["highlight_max_characters"] for item in highlights), max(map(len, highlights)), guide["highlight_max_characters"]),
            SubmissionConstraintResult("figure-caption-coverage", set(submission["figure_captions"]) == {figure for section in manuscript["sections"] for figure in section.get("figures", [])}, sorted(submission["figure_captions"]), sorted({figure for section in manuscript["sections"] for figure in section.get("figures", [])})),
        ]
        blockers = [key for key in self.REQUIRED_METADATA if not submission.get(key)]
        failed = [item.constraint_id for item in results if not item.passed]
        return {
            "schema_version": "aei-submission-validation-v1",
            "package_ready": not blockers and not failed,
            "constraint_results": [item.__dict__ for item in results],
            "metadata_blockers": blockers,
            "failed_constraints": failed,
        }


class LatexEscaper:
    REPLACEMENTS = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }

    def escape(self, text: str) -> str:
        return "".join(self.REPLACEMENTS.get(character, character) for character in text)


class AEILatexRenderer:
    """Render structured evidence as an editable elsarticle source."""

    CITATION = re.compile(r"\[cite:([^\]]+)\]")

    def __init__(self) -> None:
        self._escaper = LatexEscaper()

    def _prose(self, text: str) -> str:
        parts = []
        cursor = 0
        for match in self.CITATION.finditer(text):
            parts.append(self._escaper.escape(text[cursor:match.start()]))
            keys = ",".join(item.strip() for item in match.group(1).split(","))
            parts.append(r"\cite{" + keys + "}")
            cursor = match.end()
        parts.append(self._escaper.escape(text[cursor:]))
        return "".join(parts).replace("https://github.com/mingwucn/GearRL", r"\url{https://github.com/mingwucn/GearRL}")

    def _table(self, path: Path, caption: str) -> str:
        rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in path.read_text().splitlines() if line.startswith("|")]
        rows = [row for index, row in enumerate(rows) if index != 1]
        columns = len(rows[0])
        body = []
        for index, row in enumerate(rows):
            cells = [self._escaper.escape(cell) for cell in row]
            if index == 0:
                cells = [r"\textbf{" + cell + "}" for cell in cells]
            body.append(" & ".join(cells) + r" \\")
            if index == 0:
                body.append(r"\hline")
        return "\n".join([r"\begin{table}[htbp]", r"\centering", r"\caption{" + self._escaper.escape(caption) + "}", r"\small", r"\begin{tabular}{" + "l" * columns + "}", *body, r"\end{tabular}", r"\end{table}"])

    def render(self, manuscript: dict, submission: dict, literature: dict, publication_root: Path) -> str:
        registry = json.loads((publication_root / "registry.json").read_text())
        tables = {item["table_id"]: publication_root / item["output"] for item in registry["tables"]}
        figure_numbers: dict[str, int] = {}
        lines = [
            r"\documentclass[preprint,12pt]{elsarticle}",
            r"\usepackage[T1]{fontenc}", r"\usepackage{hyperref}", r"\usepackage{svg}",
            r"\journal{Advanced Engineering Informatics}", r"\begin{document}", r"\begin{frontmatter}",
            r"\title{" + self._escaper.escape(manuscript["title"]) + "}",
            r"\author{Author metadata required before submission}",
            r"\begin{abstract}", self._prose(manuscript["abstract"]), r"\end{abstract}",
            r"\begin{keyword}", " \sep ".join(self._escaper.escape(item) for item in manuscript["keywords"]), r"\end{keyword}",
            r"\end{frontmatter}",
        ]
        for section in manuscript["sections"]:
            title = re.sub(r"^\d+\.\s*", "", section["title"])
            lines.extend([r"\section{" + self._escaper.escape(title) + "}"])
            lines.extend(self._prose(paragraph) + "\n" for paragraph in section["paragraphs"])
            for table_id in section.get("tables", []):
                lines.append(self._table(tables[table_id], table_id.replace("-", " ").title()))
            for figure_id in section.get("figures", []):
                number = len(figure_numbers) + 1
                figure_numbers[figure_id] = number
                lines.extend([r"\begin{figure}[htbp]", r"\centering", rf"\includesvg[inkscapelatex=false,width=\linewidth]{{Figure_{number}.svg}}", r"\caption{" + self._escaper.escape(submission["figure_captions"][figure_id]) + "}", r"\end{figure}"])
        lines.extend([r"\begin{thebibliography}{99}"])
        for method in sorted(literature["methods"], key=lambda item: (item["year"], item["id"])):
            entry = f"{method['title']}. {method['venue']} ({method['year']}). https://doi.org/{method['doi']}"
            lines.append(r"\bibitem{" + method["id"] + "}" + self._prose(entry))
        lines.extend([r"\end{thebibliography}", r"\end{document}", ""])
        return "\n".join(lines)


class AEISubmissionPackageStore:
    """Build and byte-reproduce the provisional editable submission bundle."""

    @staticmethod
    def _encode(payload: Any) -> bytes:
        return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()

    def build(self, manuscript_source: Path, submission_source: Path, literature_path: Path, publication_root: Path, output: Path) -> Path:
        if output.exists() and any(output.iterdir()):
            raise FileExistsError("Submission package destination must be empty")
        output.mkdir(parents=True, exist_ok=True)
        manuscript = json.loads(manuscript_source.read_text())
        submission = json.loads(submission_source.read_text())
        literature = json.loads(literature_path.read_text())
        ManuscriptCitationResolver(literature["methods"]).validate_coverage(json.dumps(manuscript))
        validation = AEISubmissionValidator().validate(manuscript, submission)
        (output / "validation.json").write_bytes(self._encode(validation))
        tex = AEILatexRenderer().render(manuscript, submission, literature, publication_root).encode()
        ManuscriptClaimGuard().validate(tex.decode())
        (output / "manuscript.tex").write_bytes(tex)
        (output / "highlights.txt").write_text("\n".join(f"- {item}" for item in submission["highlights"]) + "\n")
        captions = []
        registry = json.loads((publication_root / "registry.json").read_text())
        figures = {item["figure_id"]: publication_root / item["output"] for item in registry["figures"]}
        used_figures = [figure for section in manuscript["sections"] for figure in section.get("figures", [])]
        for number, figure_id in enumerate(used_figures, 1):
            shutil.copyfile(figures[figure_id], output / f"Figure_{number}.svg")
            captions.append(f"Figure {number}. {submission['figure_captions'][figure_id]}")
        (output / "figure_captions.txt").write_text("\n\n".join(captions) + "\n")
        source_paths = [manuscript_source, submission_source, literature_path, publication_root / "registry.json"]
        outputs = sorted(path for path in output.iterdir() if path.is_file())
        manifest = {
            "schema_version": "aei-submission-package-v1",
            "sources": [{"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest()} for path in source_paths],
            "outputs": [{"path": path.name, "sha256": sha256(path.read_bytes()).hexdigest()} for path in outputs],
        }
        path = output / "manifest.json"
        path.write_bytes(self._encode(manifest))
        return path

    def verify(self, root: Path) -> dict[str, Any]:
        manifest = json.loads((root / "manifest.json").read_text())
        for item in manifest["sources"]:
            if sha256(Path(item["path"]).read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError(f"Submission source hash mismatch: {item['path']}")
        for item in manifest["outputs"]:
            if sha256((root / item["path"]).read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError(f"Submission output hash mismatch: {item['path']}")
        return json.loads((root / "validation.json").read_text())

    def verify_reproduction(self, frozen: Path) -> None:
        manifest = json.loads((frozen / "manifest.json").read_text())
        self.verify(frozen)
        source = {Path(item["path"]).name: Path(item["path"]) for item in manifest["sources"]}
        with TemporaryDirectory(prefix="gearrl-aei-package-") as temporary:
            generated = Path(temporary)
            publication_root = source["registry.json"].parent
            self.build(source["manuscript_source.json"], source["aei_submission_source.json"], source["aei_closest_methods.json"], publication_root, generated)
            frozen_files = {path.name: path.read_bytes() for path in frozen.iterdir() if path.is_file()}
            generated_files = {path.name: path.read_bytes() for path in generated.iterdir() if path.is_file()}
            if frozen_files != generated_files:
                raise ValueError("Regenerated AEI submission package is not byte-identical")
