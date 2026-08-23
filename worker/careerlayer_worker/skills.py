import re
from dataclasses import dataclass, field
from typing import NamedTuple

from careerlayer.integrity.models import BBox, Finding, Severity

VOCABULARY: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "FastAPI": ("fastapi", "fast api"),
    "Django": ("django",),
    "Flask": ("flask",),
    "JavaScript": ("javascript", "js"),
    "TypeScript": ("typescript",),
    "React": ("react", "react.js", "reactjs"),
    "Next.js": ("next.js", "nextjs"),
    "Node.js": ("node.js", "nodejs", "node"),
    "Java": ("java",),
    "Go": ("golang",),
    "Rust": ("rust",),
    "C++": ("c++",),
    "SQL": ("sql",),
    "PostgreSQL": ("postgresql", "postgres"),
    "MySQL": ("mysql",),
    "MongoDB": ("mongodb", "mongo"),
    "Redis": ("redis",),
    "Kafka": ("kafka", "apache kafka"),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "AWS": ("aws", "amazon web services"),
    "GCP": ("gcp", "google cloud"),
    "Azure": ("azure",),
    "Terraform": ("terraform",),
    "CI/CD": ("ci/cd", "cicd", "continuous integration"),
    "GraphQL": ("graphql",),
    "REST": ("rest", "restful"),
    "Microservices": ("microservices", "microservice"),
    "Machine Learning": ("machine learning", "ml"),
    "PyTorch": ("pytorch",),
    "TensorFlow": ("tensorflow",),
    "Pandas": ("pandas",),
    "Spark": ("spark", "apache spark"),
    "Airflow": ("airflow", "apache airflow"),
    "Git": ("git",),
    "Linux": ("linux",),
}

SOURCE = "dictionary_v1"

_FLAGGED = frozenset({Severity.SUSPICIOUS, Severity.HIGH})

# Half the span inside a flagged rectangle is enough. Findings are reported at line or
# character granularity and spans at run granularity, so demanding containment would miss
# the overlap almost every time.
_OVERLAP_FLOOR = 0.5


@dataclass
class SkillMatch:
    canonical_name: str
    span_indices: list[int] = field(default_factory=list)
    flagged_span_indices: list[int] = field(default_factory=list)

    @property
    def support_count(self) -> int:
        return len(self.span_indices)

    @property
    def flagged_support_count(self) -> int:
        return len(self.flagged_span_indices)

    @property
    def confidence(self) -> float:
        """Derived from evidence, never asserted.

        Two independent inputs, both stored on the row so the number can be checked by hand:
        how many distinct spans mention the term, and how many of those an integrity detector
        flagged. One mention is 0.6; more mentions add a little, saturating well below
        certainty because a dictionary match is not proof of competence.

        Evidence sitting inside flagged text is discounted hard, and a skill whose only
        support is hidden text lands near the floor. That is the point: a term that only
        exists where a human cannot see it should not read as a verified skill.
        """
        base = min(0.6 + 0.1 * (self.support_count - 1), 0.9)
        if self.flagged_support_count == 0:
            return round(base, 3)
        clean = self.support_count - self.flagged_support_count
        if clean == 0:
            return 0.15
        return round(base * (clean / self.support_count), 3)


class SpanRef(NamedTuple):
    page: int
    bbox: BBox
    text: str


def extract(spans: list[SpanRef], findings: list[Finding]) -> list[SkillMatch]:
    """Match a curated vocabulary against the text layer, span by span.

    A dictionary rather than a model, because phase 2 has no LLM in the pipeline and an
    unexplainable skill list would be exactly the opaque score this product refuses to ship.
    Every match points at the span it came from, so a reviewer can click through to the text.

    A span counts as flagged when it overlaps the rectangle of a suspicious or high finding,
    not merely when it shares a page with one. Page granularity would discount every skill on
    a page containing a single hidden line, which would punish the honest half of the
    document for the dishonest half.

    The obvious limitation is that it finds only what the vocabulary knows. That is recorded
    rather than hidden: `source` is stored on every row so a later extractor can be told
    apart from this one.
    """
    flagged = [f for f in findings if f.severity in _FLAGGED]
    matches: dict[str, SkillMatch] = {}
    for index, span in enumerate(spans):
        haystack = span.text.casefold()
        hit_names = [
            canonical
            for canonical, aliases in VOCABULARY.items()
            if any(_contains_term(haystack, alias) for alias in aliases)
        ]
        if not hit_names:
            continue
        inside_flagged = _overlaps_flagged(span, flagged)
        for canonical in hit_names:
            match = matches.setdefault(canonical, SkillMatch(canonical_name=canonical))
            match.span_indices.append(index)
            if inside_flagged:
                match.flagged_span_indices.append(index)
    return sorted(matches.values(), key=lambda m: (-m.confidence, m.canonical_name))


def _overlaps_flagged(span: SpanRef, flagged: list[Finding]) -> bool:
    return any(
        finding.page == span.page and span.bbox.contained_fraction(finding.bbox) >= _OVERLAP_FLOOR
        for finding in flagged
    )


def _contains_term(haystack: str, term: str) -> bool:
    """Whole-term match only.

    Substring matching turns "Go" into a hit on "Django" and "R" into a hit on everything.
    The term is escaped because the vocabulary contains "c++" and "ci/cd".
    """
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", haystack) is not None
