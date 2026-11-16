# Other imports
from collections.abc import Callable, Iterable
from datetime import timedelta
from typing import Any

# Django imports
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection
from django.db.models import Count, Model, QuerySet
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

# Model imports
from apps.auths.models import User
from apps.blog.models import Post
from apps.blog.queries import QUERIES

ROWS_TO_SHOW = 5
WRITE_QUERIES = range(40, 45)
SAMPLE_DAYS = 30
SAMPLE_MIN_TAG_POSTS = 10
SAMPLE_NAME_PREFIX_LENGTH = 3
MIN_TAGS_FOR_BOTH = 2
INDENT = "  "


# Helpers that read sample values from the database (run before counting SQL)
def _post_slug() -> str | None:
    return Post.objects.values_list("slug", flat=True).first()


def _title_word() -> str:
    title = Post.objects.values_list("title", flat=True).first() or ""
    return title.split()[0] if title else ""


def _author_email() -> str | None:
    return (
        User.objects.filter(posts__status=Post.Status.PUBLISHED)
        .values_list("email", flat=True)
        .first()
    )


def _two_tag_slugs() -> dict[str, str]:
    post = (
        Post.objects.annotate(tag_count=Count("tags"))
        .filter(tag_count__gte=MIN_TAGS_FOR_BOTH)
        .first()
    )
    slugs = list(post.tags.values_list("slug", flat=True)[:MIN_TAGS_FOR_BOTH]) if post else ["", ""]
    return {"first_slug": slugs[0], "second_slug": slugs[1]}


def _full_name_part() -> str:
    user = User.objects.exclude(first_name="").first()
    if user is None:
        return ""
    return f"{user.first_name} {user.second_name[:SAMPLE_NAME_PREFIX_LENGTH]}"


def _today_minus(days: int) -> Callable[[], Any]:
    return lambda: (timezone.now() - timedelta(days=days)).date()


# {number: {argument: value}}. A callable value is resolved before the query runs.
# A callable in place of the whole dict returns several arguments at once.
QUERY_ARGUMENTS: dict[int, dict[str, Any] | Callable[[], dict[str, Any]]] = {
    4: {"slug": _post_slug},
    7: {"page": 1},
    8: {"word": _title_word},
    9: {"domain": "gmail.com"},
    11: {"slugs": ["python", "django", "devops"]},
    12: {"year": lambda: timezone.now().year, "month": lambda: timezone.now().month},
    13: {"days": SAMPLE_DAYS},
    14: {"start": _today_minus(SAMPLE_DAYS), "end": lambda: timezone.now().date()},
    15: {"email": _author_email},
    16: {"tag_slug": "python"},
    17: {"category_slug": "python"},
    21: _two_tag_slugs,
    22: {"text": _title_word},
    34: {"min_posts": SAMPLE_MIN_TAG_POSTS},
    37: {"text": _full_name_part},
    40: {"name": "Django ORM"},
    41: {"days": SAMPLE_DAYS},
    42: {"category_slug": "python", "tag_slug": "tutorial"},
    43: {"source_slug": "devops", "target_slug": "python"},
}


def resolve_arguments(number: int) -> dict[str, Any]:
    """Turn the sample arguments of a query into real values."""
    arguments = QUERY_ARGUMENTS.get(number, {})
    if callable(arguments):
        return arguments()
    return {name: value() if callable(value) else value for name, value in arguments.items()}


class Command(BaseCommand):
    help = "Run the ORM queries from apps/blog/queries.py and show results and SQL counts."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--number", type=int, help="Run only this query (also works for 40–44)")
        parser.add_argument("--sql", action="store_true", help="Print the SQL sent to the database")

    def handle(self, *args: Any, **options: Any) -> None:
        number: int | None = options["number"]
        show_sql: bool = options["sql"]

        if number is not None:
            if number not in QUERIES:
                raise CommandError(f"Query #{number} does not exist. Choose from 1 to {max(QUERIES)}.")
            numbers = [number]
        else:
            numbers = [n for n in sorted(QUERIES) if n not in WRITE_QUERIES]

        for current in numbers:
            self.run_query(current, show_sql)

    def run_query(self, number: int, show_sql: bool) -> None:
        function = QUERIES[number]
        arguments = resolve_arguments(number)

        with CaptureQueriesContext(connection) as context:
            result = function(**arguments)
            annotations: list[str] = []
            if isinstance(result, QuerySet):
                annotations = list(result.query.annotations)
                result = list(result)

        count = len(context.captured_queries)
        noun = "query" if count == 1 else "queries"
        self.stdout.write(self.style.SUCCESS(f"#{number} {function.__name__} — {count} SQL {noun}"))
        if show_sql:
            for captured in context.captured_queries:
                self.stdout.write(captured["sql"])

        self.write_result(result, annotations)

    def write_result(self, result: Any, annotations: list[str]) -> None:
        if isinstance(result, dict) and all(isinstance(value, list) for value in result.values()) and result:
            self.write_rows([f"{key}: {value}" for key, value in result.items()], len(result))
        elif isinstance(result, list):
            rows = [self.format_row(row, annotations) for row in result[:ROWS_TO_SHOW]]
            self.write_rows(rows, len(result))
        else:
            self.stdout.write(f"{INDENT}{self.format_row(result, annotations)}")

    def write_rows(self, rows: Iterable[str], total: int) -> None:
        for row in rows:
            self.stdout.write(f"{INDENT}{row}")
        self.stdout.write(f"{INDENT}({total} rows)")

    @staticmethod
    def format_row(row: Any, annotations: list[str]) -> str:
        if isinstance(row, Model) and annotations:
            values = {name: getattr(row, name) for name in annotations}
            return f"{row} {values}"
        return str(row)
