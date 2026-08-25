import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

from careerlayer.integrity import parse, run
from careerlayer.integrity.errors import ExtractionFailed
from careerlayer_api import storage
from careerlayer_api.jd_intake import (
    RejectedJob,
    normalize_job_text,
)
from careerlayer_api.models import (
    JobDescription,
    JobSource,
    JobState,
)
from careerlayer_api.observability import configure, log
from careerlayer_api.settings import get_settings

from .db import session_scope

configure()


def process_job_description(job_description_id: str) -> str:
    """Process an uploaded PDF or queued job description without calling any LLM."""
    with session_scope() as session:
        job = session.get(JobDescription, uuid.UUID(job_description_id))
        if job is None:
            log("jd_processing_skipped_missing", job_description_id=job_description_id)
            return "missing"
        if job.state == JobState.COMPLETED:
            log("jd_processing_already_completed", job_description_id=job_description_id)
            return "completed"
        job.state = JobState.PROCESSING
        job.failure_code = None
        session.flush()
        log("jd_processing_started", job_description_id=job_description_id)

    try:
        _run_jd_pipeline(job_description_id)
    except (ExtractionFailed, RejectedJob, RuntimeError, ValueError) as exc:
        return _fail_jd(job_description_id, "extraction_failed", exc)
    except storage.StorageUnavailable as exc:
        return _fail_jd(job_description_id, "storage_unavailable", exc)

    log("jd_processing_completed", job_description_id=job_description_id)
    return "completed"


def _run_jd_pipeline(job_description_id: str) -> None:
    settings = get_settings()
    with session_scope() as session:
        job = session.get(JobDescription, uuid.UUID(job_description_id))
        if job is None:
            return
        source = job.source
        storage_key = job.storage_key

    if source == JobSource.UPLOADED and storage_key:
        content = storage.get(storage_key)
        with TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
            pdf_path = Path(scratch) / "job.pdf"
            pdf_path.write_bytes(content)

            document = parse(pdf_path, dpi=settings.render_dpi)
            findings = run(document)
            log(
                "jd_integrity_scanned",
                job_description_id=job_description_id,
                findings_count=len(findings),
            )

            # Extract full raw text from spans
            page_texts: list[str] = []
            for page in document.pages:
                spans_text = " ".join(s.text for s in page.spans if s.text.strip())
                if spans_text:
                    page_texts.append(spans_text)
            extracted_raw = "\n\n".join(page_texts) or (job.raw_text or "")

            normalized = normalize_job_text(extracted_raw)

            with session_scope() as session:
                job_to_update = session.get(JobDescription, uuid.UUID(job_description_id))
                if job_to_update is not None:
                    job_to_update.raw_text = extracted_raw
                    job_to_update.normalized_text = normalized.normalized_text
                    job_to_update.sha256 = normalized.sha256
                    job_to_update.page_count = document.page_count
                    job_to_update.state = JobState.COMPLETED
                    job_to_update.failure_code = None
    else:
        # Pasted JD
        with session_scope() as session:
            job_to_update = session.get(JobDescription, uuid.UUID(job_description_id))
            if job_to_update is not None:
                normalized = normalize_job_text(job_to_update.raw_text)
                job_to_update.normalized_text = normalized.normalized_text
                job_to_update.sha256 = normalized.sha256
                job_to_update.state = JobState.COMPLETED
                job_to_update.failure_code = None


def _fail_jd(job_description_id: str, code: str, exc: Exception) -> str:
    log(
        "jd_processing_failed",
        job_description_id=job_description_id,
        code=code,
        error_type=type(exc).__name__,
    )
    with session_scope() as session:
        job = session.get(JobDescription, uuid.UUID(job_description_id))
        if job is not None:
            job.state = JobState.FAILED
            job.failure_code = code
    return "failed"
