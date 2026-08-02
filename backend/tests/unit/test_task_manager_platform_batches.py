from types import SimpleNamespace

from services import task_manager as task_manager_module
from services.task_manager import (
    _safe_visual_fallback_prompt,
    apply_batch_terminal_state,
    apply_image_terminal_state,
)


class FakeTask:
    def __init__(self, progress=None):
        self.status = "PROCESSING"
        self.error_message = None
        self.completed_at = None
        self.progress = progress or {}

    def get_progress(self):
        return self.progress

    def set_progress(self, progress):
        self.progress = progress


class FakePageQuery:
    def __init__(self, pages):
        self.pages = pages

    def filter_by(self, **_kwargs):
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        return self.pages


class FakeFileService:
    @staticmethod
    def get_absolute_path(path):
        return path


def test_batch_with_failed_pages_is_not_reported_completed():
    task = SimpleNamespace(status="PROCESSING", error_message=None, completed_at=None)

    apply_batch_terminal_state(task, failed=3, total=3, label="Image")

    assert task.status == "FAILED"
    assert task.error_message == "Image generation failed for 3/3 pages"
    assert task.completed_at is not None


def test_successful_batch_clears_previous_error():
    task = SimpleNamespace(
        status="PROCESSING",
        error_message="previous attempt failed",
        completed_at=None,
    )

    apply_batch_terminal_state(task, failed=0, total=3, label="Description")

    assert task.status == "COMPLETED"
    assert task.error_message is None


def test_image_batch_retains_readable_images_from_previous_attempt(monkeypatch, tmp_path):
    retained_path = tmp_path / "retained.png"
    generated_path = tmp_path / "generated.png"
    retained_path.write_bytes(b"retained")
    generated_path.write_bytes(b"generated")
    pages = [
        SimpleNamespace(id="page-1", order_index=0, generated_image_path=str(retained_path)),
        SimpleNamespace(id="page-2", order_index=1, generated_image_path=str(generated_path)),
    ]
    monkeypatch.setattr(
        task_manager_module,
        "Page",
        SimpleNamespace(query=FakePageQuery(pages), order_index=None),
    )
    task = FakeTask({"warning_message": "resolution mismatch"})

    apply_image_terminal_state(
        task,
        "project-1",
        FakeFileService(),
        generated_page_ids={"page-2"},
        attempt_errors={"page-1": RuntimeError("MODEL_CALL_FAILED")},
    )

    assert task.status == "COMPLETED"
    assert task.progress["generated"] == 1
    assert task.progress["retained"] == 1
    assert task.progress["available"] == 2
    assert task.progress["missing"] == 0
    assert task.progress["warning_message"] == "resolution mismatch"


def test_image_batch_reports_only_truly_missing_pages(monkeypatch, tmp_path):
    retained_path = tmp_path / "retained.png"
    retained_path.write_bytes(b"retained")
    pages = [
        SimpleNamespace(id="page-1", order_index=0, generated_image_path=str(retained_path)),
        SimpleNamespace(id="page-2", order_index=1, generated_image_path=str(tmp_path / "gone.png")),
    ]
    monkeypatch.setattr(
        task_manager_module,
        "Page",
        SimpleNamespace(query=FakePageQuery(pages), order_index=None),
    )
    task = FakeTask()

    apply_image_terminal_state(
        task,
        "project-1",
        FakeFileService(),
        generated_page_ids=set(),
        attempt_errors={"page-2": RuntimeError("MODEL_005 rejected")},
    )

    assert task.status == "FAILED"
    assert task.progress["error_code"] == "IMAGE_PARTIAL_FAILURE"
    assert task.progress["available"] == 1
    assert task.progress["missing_page_ids"] == ["page-2"]
    assert task.progress["missing_page_numbers"] == [2]
    assert task.progress["page_errors"] == [{
        "pageId": "page-2",
        "pageNo": 2,
        "code": "MODEL_005",
        "message": "页面内容未通过模型安全检查，已尝试安全视觉降级",
    }]


def test_safety_visual_fallback_is_appended_at_most_once():
    once = _safe_visual_fallback_prompt("original prompt")
    twice = _safe_visual_fallback_prompt(once)

    assert once == twice
    assert once.count("<safety_visual_fallback>") == 1
