import logging

from apps.courses.judgenew.runner import RunResult, run_in_sandbox

logger = logging.getLogger(__name__)


def normalize_output(text: str) -> str:
    return (text or "").strip().replace("\r\n", "\n").replace("\r", "\n")


def evaluate(problem, language: str, source_code: str) -> tuple[str, str | None]:
    """
    Barcha test-case larni tekshiradi.
    Returns: ("accepted" | "rejected" | "error", error_message | None)
    """
    tests = problem.tests.all().order_by("id")

    if not tests.exists():
        return ("error", "Testlar topilmadi")

    for index, t in enumerate(tests, start=1):
        result: RunResult = run_in_sandbox(language, source_code, t.input_data)

        if result.timeout:
            return ("error", f"Test #{index}: Vaqt limiti oshib ketdi (TLE)")

        if not result.ok:
            err = (result.stderr or "Runtime/Compile error")[:2000]
            return ("error", f"Test #{index}: {err}")

        got = normalize_output(result.stdout)
        expected = normalize_output(t.output_data)

        if got != expected:
            return (
                "rejected",
                f"Test #{index}: Noto'g'ri javob.\n"
                f"Kutilgan: {expected[:200]!r}\n"
                f"Olingan: {got[:200]!r}",
            )

        logger.debug("Test #%s passed for problem %s", index, problem.pk)

    return ("accepted", None)
