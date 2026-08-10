import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import Base  # noqa: E402
from models import Item, Job  # noqa: E402
from services.job_manager import JobManager  # noqa: E402


def create_test_session():
    engine = create_engine('sqlite:///:memory:')
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_cancel_job_marks_job_canceled_and_stops_item():
    db = create_test_session()
    manager = JobManager(db)

    try:
        job = manager.create_job(
            youtube_url='https://www.youtube.com/watch?v=test123',
            language='ja',
            model='gpt-4o-mini-transcribe',
            user_title='cancel target',
        )

        manager.update_job_status(job.id, 'processing')
        manager.update_job_progress(job.id, 42)
        canceled = manager.cancel_job(job.id)

        assert canceled is not None

        db.expire_all()
        stored_job = db.query(Job).filter(Job.id == job.id).first()
        stored_item = db.query(Item).filter(Item.job_id == job.id).first()

        assert stored_job is not None
        assert stored_job.status == 'canceled'
        assert stored_job.error_message == 'ユーザーにより取消されました'
        assert stored_item is not None
        assert stored_item.status == 'failed'
        assert stored_item.error_message == 'ユーザーにより取消されました'
    finally:
        db.close()


def test_canceled_job_ignores_later_status_and_progress_updates():
    db = create_test_session()
    manager = JobManager(db)

    try:
        job = manager.create_job(
            youtube_url='https://www.youtube.com/watch?v=test456',
            language='en',
            model='gpt-4o-mini-transcribe',
        )

        manager.update_job_progress(job.id, 10)
        manager.cancel_job(job.id)
        manager.update_job_progress(job.id, 95)
        manager.update_job_status(job.id, 'completed')

        db.expire_all()
        stored_job = db.query(Job).filter(Job.id == job.id).first()

        assert stored_job is not None
        assert stored_job.status == 'canceled'
        assert stored_job.progress == 10
    finally:
        db.close()