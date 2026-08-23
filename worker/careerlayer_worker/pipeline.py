import time
import uuid
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
from PIL.Image import Image
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from careerlayer.integrity import ParsedDocument, parse, run
from careerlayer.integrity.errors import ExtractionFailed, OcrUnavailable, RenderFailed
from careerlayer.integrity.models import Finding as IntegrityFinding
from careerlayer.integrity.rendered_layer import render_page
from careerlayer_api import storage
from careerlayer_api.models import (
    Extraction,
    FailureCode,
    Finding,
    ProcessingState,
    Resume,
    ResumePage,
    ResumeSkill,
    SkillEvidence,
    TextSpan,
)
from careerlayer_api.observability import configure, log
from careerlayer_api.settings import get_settings

from . import skills
from .db import session_scope

configure()


def process_resume(resume_id: str) -> str:
    """Turn an uploaded PDF into pages, spans, findings and skills.

    Every step that can fail maps to a FailureCode the user is allowed to see. The exception
    itself goes to the log with the resume id and never crosses the API boundary, because an
    exception message here can carry a storage endpoint, a DSN, or a line of somebody's
    resume.
    """
    with session_scope() as session:
        resume = session.get(Resume, uuid.UUID(resume_id))
        if resume is None:
            log("processing_skipped_missing_resume", resume_id=resume_id)
            return "missing"
        resume.state = ProcessingState.PROCESSING
        resume.failure_code = None
        session.flush()
        log("processing_started", resume_id=resume_id)

    try:
        _run(resume_id)
    except (ExtractionFailed, RuntimeError, ValueError) as exc:
        return _fail(resume_id, FailureCode.EXTRACTION_FAILED, exc)
    except RenderFailed as exc:
        return _fail(resume_id, FailureCode.RENDER_FAILED, exc)
    except OcrUnavailable as exc:
        return _fail(resume_id, FailureCode.OCR_UNAVAILABLE, exc)
    except storage.StorageUnavailable as exc:
        return _fail(resume_id, FailureCode.STORAGE_UNAVAILABLE, exc)

    log("processing_completed", resume_id=resume_id)
    return "completed"


def _run(resume_id: str) -> None:
    settings = get_settings()
    with session_scope() as session:
        resume = session.get(Resume, uuid.UUID(resume_id))
        if resume is None:
            return
        storage_key = resume.storage_key

    content = storage.get(storage_key)

    with TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
        # The integrity package takes a path, not bytes: it is a standalone library that
        # knows nothing about object storage, and keeping it that way is what lets the CLI
        # run with no infrastructure.
        pdf_path = Path(scratch) / "resume.pdf"
        pdf_path.write_bytes(content)

        started = time.monotonic()
        document = parse(pdf_path, dpi=settings.render_dpi)
        duration_ms = int((time.monotonic() - started) * 1000)
        log(
            "text_extraction_completed",
            resume_id=resume_id,
            pages=document.page_count,
            spans=sum(len(page.spans) for page in document.pages),
        )
        log("ocr_completed", resume_id=resume_id, available=document.ocr_available)

        renders = _render_pages(resume_id, pdf_path, settings.render_dpi)
        log("rendering_completed", resume_id=resume_id, pages=len(renders))

        findings = run(document)
        log(
            "integrity_analysis_completed",
            resume_id=resume_id,
            findings=len(findings),
            high=sum(1 for f in findings if f.severity.value == "high"),
        )

    with session_scope() as session:
        _persist(session, resume_id, document, renders, findings, duration_ms)


def _render_pages(resume_id: str, pdf_path: Path, dpi: int) -> dict[int, tuple[str, int, int]]:
    """Rasterise every page once, at upload time, and keep the PNG.

    Rendering on demand would repeat this work on every viewer open. Pages are immutable
    once analysed, so the render is cached forever rather than recomputed.
    """
    renders: dict[int, tuple[str, int, int]] = {}
    document = pymupdf.open(pdf_path)
    try:
        for index in range(document.page_count):
            page_number = index + 1
            image = render_page(document[index], dpi=dpi)
            key = storage.page_render_key(resume_id, page_number)
            buffer = _png_bytes(image)
            storage.put(key, buffer, "image/png")
            renders[page_number] = (key, image.width, image.height)
    finally:
        document.close()
    return renders


def _png_bytes(image: Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _persist(
    session: Session,
    resume_id: str,
    document: ParsedDocument,
    renders: dict[int, tuple[str, int, int]],
    findings: list[IntegrityFinding],
    duration_ms: int,
) -> None:
    resume = session.get(Resume, uuid.UUID(resume_id))
    if resume is None:
        return

    _clear_previous(session, resume.id)

    extraction = Extraction(
        resume_id=resume.id,
        method="text_layer" if not document.ocr_available else "text_layer+ocr",
        page_count=document.page_count,
        duration_ms=duration_ms,
    )
    session.add(extraction)
    session.flush()

    span_rows: list[TextSpan] = []
    span_refs: list[skills.SpanRef] = []
    for page in document.pages:
        key, width_px, height_px = renders.get(page.number, ("", 0, 0))
        session.add(
            ResumePage(
                resume_id=resume.id,
                page_number=page.number,
                width_pt=page.cropbox.width,
                height_pt=page.cropbox.height,
                rotation=page.rotation,
                render_key=key or None,
                render_width_px=width_px or None,
                render_height_px=height_px or None,
                render_dpi=get_settings().render_dpi if key else None,
                ocr_text=page.ocr_text or None,
            )
        )
        for span in page.spans:
            row = TextSpan(
                extraction_id=extraction.id,
                page=page.number,
                x0=span.bbox.x0,
                y0=span.bbox.y0,
                x1=span.bbox.x1,
                y1=span.bbox.y1,
                text=span.text,
                font=span.font[:120],
                font_size=span.font_size,
                colour=_hex(span.colour),
                render_mode=span.render_mode,
                opacity=span.opacity,
                seqno=span.seqno,
                char_start=span.char_start,
                char_end=span.char_end,
            )
            span_rows.append(row)
            span_refs.append(skills.SpanRef(page=page.number, bbox=span.bbox, text=span.text))
    session.add_all(span_rows)

    for finding in findings:
        session.add(
            Finding(
                resume_id=resume.id,
                detector_id=finding.detector_id,
                detector_name=finding.detector_name,
                severity=finding.severity.value,
                confidence=finding.confidence,
                page=finding.page,
                x0=finding.bbox.x0,
                y0=finding.bbox.y0,
                x1=finding.bbox.x1,
                y1=finding.bbox.y1,
                excerpt=finding.excerpt,
                rationale=finding.rationale,
            )
        )
    session.flush()

    for match in skills.extract(span_refs, findings):
        skill = ResumeSkill(
            resume_id=resume.id,
            canonical_name=match.canonical_name,
            confidence=match.confidence,
            support_count=match.support_count,
            flagged_support_count=match.flagged_support_count,
            source=skills.SOURCE,
        )
        session.add(skill)
        session.flush()
        for index in match.span_indices:
            session.add(SkillEvidence(skill_id=skill.id, span_id=span_rows[index].id))

    resume.page_count = document.page_count
    resume.state = ProcessingState.COMPLETED
    resume.failure_code = None


def _clear_previous(session: Session, resume_id: uuid.UUID) -> None:
    """Make reprocessing idempotent.

    A retried job must not double every finding, and the cheapest way to guarantee that is to
    delete what the previous attempt wrote rather than to reason about which rows it owned.
    """
    old_extractions = session.execute(
        select(Extraction.id).where(Extraction.resume_id == resume_id)
    ).scalars()
    for extraction_id in list(old_extractions):
        session.execute(delete(TextSpan).where(TextSpan.extraction_id == extraction_id))
    session.execute(delete(Extraction).where(Extraction.resume_id == resume_id))
    session.execute(delete(Finding).where(Finding.resume_id == resume_id))
    session.execute(delete(ResumeSkill).where(ResumeSkill.resume_id == resume_id))
    session.execute(delete(ResumePage).where(ResumePage.resume_id == resume_id))
    session.flush()


def _fail(resume_id: str, code: FailureCode, exc: BaseException) -> str:
    log(
        "processing_failed",
        resume_id=resume_id,
        failure_code=code.value,
        error_type=type(exc).__name__,
    )
    with session_scope() as session:
        resume = session.get(Resume, uuid.UUID(resume_id))
        if resume is not None:
            resume.state = ProcessingState.FAILED
            resume.failure_code = code
    return "failed"


def _hex(colour: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in colour)
