import json

from django.db.models import Count
from django.http import HttpRequest

from apps.auths.models import User
from settings.conf import ENV_ID
from .models import Category, Comment, Post

PRODUCTION_ENV_ID = "prod"
TOP_AUTHORS_COUNT = 5
FULL_PERCENT = 100


def environment_callback(request: HttpRequest) -> list[str]:
    if ENV_ID == PRODUCTION_ENV_ID:
        return ["Production", "danger"]
    return ["Local", "warning"]


def draft_posts_badge(request: HttpRequest) -> int:
    return Post.objects.filter(status=Post.Status.DRAFT).count()


def dashboard_callback(request: HttpRequest, context: dict) -> dict:
    published = Post.objects.filter(status=Post.Status.PUBLISHED).count()
    drafts = Post.objects.filter(status=Post.Status.DRAFT).count()
    total = published + drafts

    published_percent = 0
    draft_percent = 0
    if total > 0:
        published_percent = round(published / total * FULL_PERCENT)
        draft_percent = FULL_PERCENT - published_percent

    categories = Category.objects.annotate(post_total=Count("posts")).order_by("name")
    chart = {
        "labels": [category.name for category in categories],
        "datasets": [
            {
                "label": "Posts",
                "data": [category.post_total for category in categories],
                "backgroundColor": "#3b82f6",
            },
        ],
    }

    authors = User.objects.annotate(post_total=Count("posts")).order_by("-post_total", "email")
    author_rows = [
        [f"{author.first_name} {author.second_name}", author.email, author.post_total]
        for author in authors[:TOP_AUTHORS_COUNT]
    ]

    context.update({
        "cards": [
            {"title": "Total users", "value": User.objects.count()},
            {"title": "Published posts", "value": published},
            {"title": "Drafts", "value": drafts},
            {"title": "Comments", "value": Comment.objects.count()},
        ],
        "category_chart": json.dumps(chart),
        "top_authors": {"headers": ["Author", "Email", "Posts"], "rows": author_rows},
        "published_percent": published_percent,
        "draft_percent": draft_percent,
    })
    return context
