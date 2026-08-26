from functools import lru_cache

from redis import Redis
from rq import Queue

from .settings import get_settings

QUEUE_NAME = "resume-processing"
PROCESS_JOB = "careerlayer_worker.pipeline.process_resume"
PROCESS_JOB_DESCRIPTION = "careerlayer_worker.jd_pipeline.process_job_description"
PROCESS_MATCH = "careerlayer_worker.matching.process_match"

# Rendering and OCR of a long resume is minutes, not seconds. The timeout is generous
# because a job killed halfway leaves a resume stuck in "processing" with no findings, which
# is worse than a slow one.
JOB_TIMEOUT_SECONDS = 15 * 60


@lru_cache
def _redis() -> Redis:
    return Redis.from_url(get_settings().redis_url)


def enqueue_processing(resume_id: str) -> str:
    """Hand the resume to the worker and return the job id.

    The API deliberately references the worker's entry point by dotted path rather than
    importing it. The API image does not contain Tesseract and has no reason to; importing
    the worker would drag the whole analysis stack into a process that only needs to write a
    row and return.
    """
    queue = Queue(QUEUE_NAME, connection=_redis())
    job = queue.enqueue(PROCESS_JOB, resume_id, job_timeout=JOB_TIMEOUT_SECONDS)
    return str(job.id)


def enqueue_job_processing(job_description_id: str) -> str:
    """Hand the job description to the worker for extraction and analysis."""
    queue = Queue(QUEUE_NAME, connection=_redis())
    job = queue.enqueue(
        PROCESS_JOB_DESCRIPTION, job_description_id, job_timeout=JOB_TIMEOUT_SECONDS
    )
    return str(job.id)


def enqueue_match_processing(match_run_id: str) -> str:
    """Hand the match run to the worker for requirement evaluation and claim persistence."""
    queue = Queue(QUEUE_NAME, connection=_redis())
    job = queue.enqueue(PROCESS_MATCH, match_run_id, job_timeout=JOB_TIMEOUT_SECONDS)
    return str(job.id)
