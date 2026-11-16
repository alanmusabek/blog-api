"""50 ORM queries for Homework 3."""

# Other imports
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

# Django imports
from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    Count,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, Round, TruncMonth
from django.utils import timezone
from django.utils.text import slugify

# Model imports
from apps.auths.models import User
from apps.blog.models import Category, Comment, Post, Tag

NEWEST_POSTS_LIMIT = 5
FIRST_PAGE = 1
PAGE_SIZE = 10
EDIT_THRESHOLD = timedelta(hours=1)
UNCATEGORIZED = "Uncategorized"
AVERAGE_PRECISION = 2
TOP_AUTHORS_LIMIT = 5
FULL_NAME_SEPARATOR = " "
HOT_MIN_COMMENTS = 10
NORMAL_MIN_COMMENTS = 3
POPULARITY_HOT = "hot"
POPULARITY_NORMAL = "normal"
POPULARITY_QUIET = "quiet"
FEED_LIMIT = 50
NEWEST_WITH_TAGS_LIMIT = 20
TAG_SEPARATOR = ", "


# Level 1 — First queries
def categories_by_name() -> QuerySet[Category]:
    """All categories sorted by name A → Z."""
    return Category.objects.order_by("name")


def published_posts() -> QuerySet[Post]:
    """Published posts, newest first."""
    return Post.objects.filter(status=Post.Status.PUBLISHED).order_by("-created_at")


def newest_published_posts() -> QuerySet[Post]:
    """The 5 newest published posts."""
    return published_posts()[:NEWEST_POSTS_LIMIT]


def post_by_slug(slug: str) -> Post | None:
    """The post with this slug, or None."""
    return Post.objects.filter(slug=slug).first()


def active_users_count() -> int:
    """Number of active users that are not staff."""
    return User.objects.filter(is_active=True, is_staff=False).count()


def has_drafts() -> bool:
    """True if there is at least one draft post."""
    return Post.objects.filter(status=Post.Status.DRAFT).exists()


def published_posts_page(page: int) -> QuerySet[Post]:
    """One page (PAGE_SIZE posts) of published posts, newest first."""
    offset = (max(page, FIRST_PAGE) - FIRST_PAGE) * PAGE_SIZE
    return published_posts()[offset : offset + PAGE_SIZE]


# Level 2 — Field lookups
def posts_with_word_in_title(word: str) -> QuerySet[Post]:
    """Posts whose title contains word, case-insensitive."""
    return Post.objects.filter(title__icontains=word)


def users_with_email_domain(domain: str) -> QuerySet[User]:
    """Users whose email ends with @domain."""
    return User.objects.filter(email__iendswith=f"@{domain}")


def posts_without_category() -> QuerySet[Post]:
    """Posts that have no category."""
    return Post.objects.filter(category__isnull=True)


def categories_by_slugs(slugs: list[str]) -> QuerySet[Category]:
    """Categories whose slug is in slugs."""
    return Category.objects.filter(slug__in=slugs)


def posts_in_month(year: int, month: int) -> QuerySet[Post]:
    """Posts created in this month of this year."""
    return Post.objects.filter(created_at__year=year, created_at__month=month)


def posts_last_days(days: int) -> QuerySet[Post]:
    """Posts created in the last `days` days."""
    return Post.objects.filter(created_at__gte=timezone.now() - timedelta(days=days))


def posts_between(start: date, end: date) -> QuerySet[Post]:
    """Posts created from start to end, both days included."""
    return Post.objects.filter(created_at__date__range=(start, end))


# Level 3 — Queries across relations
def author_published_posts(email: str) -> QuerySet[Post]:
    """Published posts of the author with this email (case-insensitive)."""
    return Post.objects.filter(status=Post.Status.PUBLISHED, authors__email__iexact=email)


def posts_with_tag(tag_slug: str) -> QuerySet[Post]:
    """Posts that have the tag with this slug."""
    return Post.objects.filter(tags__slug=tag_slug)


def comments_in_category(category_slug: str) -> QuerySet[Comment]:
    """Comments on posts of the category with this slug."""
    return Comment.objects.filter(post__category__slug=category_slug)


def users_with_published_posts() -> QuerySet[User]:
    """Users with at least one published post, each once."""
    return User.objects.filter(posts__status=Post.Status.PUBLISHED).distinct()


def posts_without_tags() -> QuerySet[Post]:
    """Posts that have no tags."""
    return Post.objects.filter(tags__isnull=True)


def users_without_comments() -> QuerySet[User]:
    """Users who have never written a comment."""
    return User.objects.filter(comments__isnull=True)


def posts_with_both_tags(first_slug: str, second_slug: str) -> QuerySet[Post]:
    """Posts that have both tags."""
    return Post.objects.filter(tags__slug=first_slug).filter(tags__slug=second_slug)


# Level 4 — Q and F
def search_posts(text: str) -> QuerySet[Post]:
    """Posts with text in the title or in the body, case-insensitive."""
    return Post.objects.filter(Q(title__icontains=text) | Q(body__icontains=text))


def published_posts_missing_info() -> QuerySet[Post]:
    """Published posts with no category or no tags, each once."""
    return (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .filter(Q(category__isnull=True) | Q(tags__isnull=True))
        .distinct()
    )


def edited_posts() -> QuerySet[Post]:
    """Posts edited more than EDIT_THRESHOLD after they were created."""
    return Post.objects.filter(updated_at__gt=F("created_at") + EDIT_THRESHOLD)


def comments_by_post_author() -> QuerySet[Comment]:
    """Comments that the post author wrote under their own post."""
    return Comment.objects.filter(author=F("post__authors"))


def comments_before_post() -> QuerySet[Comment]:
    """Comments created before their post. Must be empty."""
    return Comment.objects.filter(created_at__lt=F("post__created_at"))


# Level 5 — values and values_list
def published_authors_emails() -> list[str]:
    """Unique emails of authors with published posts, sorted A → Z."""
    return list(
        User.objects.filter(posts__status=Post.Status.PUBLISHED)
        .values_list("email", flat=True)
        .distinct()
        .order_by("email")
    )


def published_posts_overview() -> list[dict[str, Any]]:
    """title, author_email and category_name for every published post."""
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED).values(
            "title",
            author_email=F("authors__email"),
            category_name=Coalesce("category__name", Value(UNCATEGORIZED)),
        )
    )


# Level 6 — aggregate
def posts_stats() -> dict[str, Any]:
    """Post counts and first/last post dates in one query."""
    return Post.objects.aggregate(
        total=Count("pk"),
        published=Count("pk", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("pk", filter=Q(status=Post.Status.DRAFT)),
        first_post_at=Min("created_at"),
        last_post_at=Max("created_at"),
    )


def average_comments_per_post() -> float:
    """Average number of comments on a published post, rounded to 2 digits."""
    result = (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(comment_count=Count("comments"))
        .aggregate(average=Round(Avg("comment_count", default=0.0), AVERAGE_PRECISION))
    )
    return float(result["average"])


# Level 7 — annotate
def categories_with_post_count() -> QuerySet[Category]:
    """Every category with post_count, most posts first, then by name."""
    return Category.objects.annotate(post_count=Count("posts")).order_by("-post_count", "name")


def categories_with_published_count() -> QuerySet[Category]:
    """Every category with published_count, categories with 0 included."""
    return Category.objects.annotate(
        published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED)),
    ).order_by("-published_count", "name")


def top_authors() -> QuerySet[User]:
    """Top 5 users by number of published posts, with published_count."""
    return User.objects.annotate(
        published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED)),
    ).order_by("-published_count", "email")[:TOP_AUTHORS_LIMIT]


def popular_tags(min_posts: int) -> QuerySet[Tag]:
    """Tags used in at least min_posts posts, with post_count."""
    return (
        Tag.objects.annotate(post_count=Count("posts"))
        .filter(post_count__gte=min_posts)
        .order_by("-post_count", "name")
    )


def posts_per_status() -> list[dict[str, Any]]:
    """The number of posts for each status."""
    return list(Post.objects.values("status").annotate(count=Count("pk")).order_by("status"))


def users_activity() -> QuerySet[User]:
    """Every user with correct post_count and comment_count."""
    return User.objects.annotate(
        post_count=Count("posts", distinct=True),
        comment_count=Count("comments", distinct=True),
    ).order_by("email")


# Level 8 — Database functions and conditions
def search_users_by_full_name(text: str) -> QuerySet[User]:
    """Users whose full name ("First Last") contains text, case-insensitive."""
    return User.objects.annotate(
        full_name=Concat("first_name", Value(FULL_NAME_SEPARATOR), "second_name"),
    ).filter(full_name__icontains=text)


def published_posts_per_month() -> list[dict[str, Any]]:
    """The number of published posts in each month, oldest month first."""
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("pk"))
        .order_by("month")
    )


def posts_with_popularity() -> QuerySet[Post]:
    """Every post with comment_count and popularity (hot / normal / quiet)."""
    return Post.objects.annotate(comment_count=Count("comments")).annotate(
        popularity=Case(
            When(comment_count__gte=HOT_MIN_COMMENTS, then=Value(POPULARITY_HOT)),
            When(comment_count__gte=NORMAL_MIN_COMMENTS, then=Value(POPULARITY_NORMAL)),
            default=Value(POPULARITY_QUIET),
        )
    )


# Level 9 — Changing data
def get_or_create_tag(name: str) -> tuple[Tag, bool]:
    """Return the tag with this name, create it (slug from the name) if missing."""
    return Tag.objects.get_or_create(slug=slugify(name), defaults={"name": name})


def publish_old_drafts(days: int) -> int:
    """Publish all drafts older than `days` days in one query, return how many changed."""
    now = timezone.now()
    return Post.objects.filter(
        status=Post.Status.DRAFT,
        created_at__lt=now - timedelta(days=days),
    ).update(status=Post.Status.PUBLISHED, updated_at=now)


def tag_category_posts(category_slug: str, tag_slug: str) -> int:
    """Add the tag to every post of the category, return the number of posts in it."""
    tag = Tag.objects.get(slug=tag_slug)
    post_ids = list(Post.objects.filter(category__slug=category_slug).values_list("pk", flat=True))
    tag.posts.add(*post_ids)
    return len(post_ids)


def merge_categories(source_slug: str, target_slug: str) -> int:
    """Move posts of the source category to the target, delete the source, return moved count."""
    if source_slug == target_slug:
        raise ValueError("Source and target categories must be different")
    with transaction.atomic():
        target = Category.objects.get(slug=target_slug)
        moved = Post.objects.filter(category__slug=source_slug).update(category=target)
        Category.objects.filter(slug=source_slug).delete()
    return moved


def delete_inactive_users_comments() -> int:
    """Delete all comments of inactive users, return how many were deleted."""
    _, deleted_per_model = Comment.objects.filter(author__is_active=False).delete()
    return deleted_per_model.get(Comment._meta.label, 0)


# Level 10 — select_related and prefetch_related
def published_feed() -> list[str]:
    """The 50 newest published posts as "title | author email | category name" (1 query)."""
    posts = published_posts().select_related("authors", "category")[:FEED_LIMIT]
    return [
        f"{post.title} | {post.authors.email} | "
        f"{post.category.name if post.category else UNCATEGORIZED}"
        for post in posts
    ]


def newest_posts_with_tags() -> list[str]:
    """The 20 newest posts as "title: tag1, tag2" (at most 2 queries)."""
    posts = Post.objects.order_by("-created_at").prefetch_related(
        Prefetch("tags", queryset=Tag.objects.order_by("name")),
    )[:NEWEST_WITH_TAGS_LIMIT]
    return [f"{post.title}: {TAG_SEPARATOR.join(tag.name for tag in post.tags.all())}" for post in posts]


def categories_with_published_posts() -> dict[str, list[str]]:
    """{category name: [published post titles, newest first]} (at most 2 queries)."""
    categories = Category.objects.order_by("name").prefetch_related(
        Prefetch("posts", queryset=published_posts(), to_attr="published_posts"),
    )
    return {category.name: [post.title for post in category.published_posts] for category in categories}


# Level 11 — Subquery and Exists
def posts_with_last_comment() -> QuerySet[Post]:
    """Published posts with last_comment: the body of the newest comment or None."""
    newest_comment = Comment.objects.filter(post=OuterRef("pk")).order_by("-created_at").values("body")[:1]
    return published_posts().annotate(last_comment=Subquery(newest_comment))


def posts_with_staff_comments() -> QuerySet[Post]:
    """Posts with at least one comment from a staff user."""
    staff_comments = Comment.objects.filter(post=OuterRef("pk"), author__is_staff=True)
    return Post.objects.filter(Exists(staff_comments))


def users_with_draft_as_latest_post() -> QuerySet[User]:
    """Users whose newest post is a draft, with latest_post_status."""
    latest_status = Post.objects.filter(authors=OuterRef("pk")).order_by("-created_at", "-pk").values("status")[:1]
    return User.objects.annotate(latest_post_status=Subquery(latest_status)).filter(
        latest_post_status=Post.Status.DRAFT,
    )


QUERIES: dict[int, Callable[..., Any]] = {
    1: categories_by_name,
    2: published_posts,
    3: newest_published_posts,
    4: post_by_slug,
    5: active_users_count,
    6: has_drafts,
    7: published_posts_page,
    8: posts_with_word_in_title,
    9: users_with_email_domain,
    10: posts_without_category,
    11: categories_by_slugs,
    12: posts_in_month,
    13: posts_last_days,
    14: posts_between,
    15: author_published_posts,
    16: posts_with_tag,
    17: comments_in_category,
    18: users_with_published_posts,
    19: posts_without_tags,
    20: users_without_comments,
    21: posts_with_both_tags,
    22: search_posts,
    23: published_posts_missing_info,
    24: edited_posts,
    25: comments_by_post_author,
    26: comments_before_post,
    27: published_authors_emails,
    28: published_posts_overview,
    29: posts_stats,
    30: average_comments_per_post,
    31: categories_with_post_count,
    32: categories_with_published_count,
    33: top_authors,
    34: popular_tags,
    35: posts_per_status,
    36: users_activity,
    37: search_users_by_full_name,
    38: published_posts_per_month,
    39: posts_with_popularity,
    40: get_or_create_tag,
    41: publish_old_drafts,
    42: tag_category_posts,
    43: merge_categories,
    44: delete_inactive_users_comments,
    45: published_feed,
    46: newest_posts_with_tags,
    47: categories_with_published_posts,
    48: posts_with_last_comment,
    49: posts_with_staff_comments,
    50: users_with_draft_as_latest_post,
}
