import sys

from redis import Redis
from rq import Worker

from careerlayer_api.observability import configure, log
from careerlayer_api.queue import QUEUE_NAME
from careerlayer_api.settings import get_settings


def main() -> int:
    configure()
    settings = get_settings()
    log("worker_starting", queue=QUEUE_NAME)
    worker = Worker([QUEUE_NAME], connection=Redis.from_url(settings.redis_url))
    worker.work(with_scheduler=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
