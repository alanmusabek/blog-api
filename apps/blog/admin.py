from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.text import Truncator
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.decorators import action, display
from unfold.sections import TableSection

from .models import Category, Comment, Post, Tag

COMMENT_PREVIEW_LENGTH = 70
COMMENTS_PER_PAGE = 10


class CategoryPostsSection(TableSection):
    verbose_name = "Posts in this category"
    related_name = "posts"
    fields = ("title", "authors", "status", "created_at")


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    list_display = ("name", "slug", "post_count")
    list_sections = (CategoryPostsSection,)
    ordering = ("name",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        queryset = super().get_queryset(request)
        return queryset.annotate(post_total=Count("posts")).prefetch_related("posts__authors")

    @display(description="Posts", ordering="post_total")
    def post_count(self, obj: Category) -> int:
        return obj.post_total


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    list_display = ("name", "slug", "post_count")
    ordering = ("name",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).annotate(post_total=Count("posts"))

    @display(description="Posts", ordering="post_total")
    def post_count(self, obj: Tag) -> int:
        return obj.post_total


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("post_title", "author", "body_preview", "created_at")
    list_filter = (
        ("post", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("body", "author__email", "post__title")
    autocomplete_fields = ("post", "author")
    list_select_related = ("post", "author")
    ordering = ("-created_at",)

    @display(description="Post", ordering="post__title")
    def post_title(self, obj: Comment) -> str:
        return obj.post.title

    @display(description="Comment")
    def body_preview(self, obj: Comment) -> str:
        return Truncator(obj.body).chars(COMMENT_PREVIEW_LENGTH)


class PostCommentsSection(TableSection):
    verbose_name = "Comments on this post"
    related_name = "comments"
    fields = ("author", "body", "created_at")


class CommentInline(TabularInline):
    model = Comment
    tab = True
    extra = 0
    per_page = COMMENTS_PER_PAGE
    ordering = ("-created_at",)
    fields = ("author", "body", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author",)


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = ("post_header", "status_label", "category_name", "tags_dropdown", "comment_count", "created_at")
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("tags", MultipleRelatedDropdownFilter),
        ("authors", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("title", "authors__email")
    autocomplete_fields = ("authors", "category", "tags")
    list_select_related = ("authors", "category")
    list_sections = (PostCommentsSection,)
    ordering = ("-created_at",)
    inlines = (CommentInline,)
    warn_unsaved_form = True
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Content", {"classes": ("tab",), "fields": ("title",)}),
        ("Classification", {"classes": ("tab",), "fields": ("category", "tags", "status")}),
        ("Meta", {"classes": ("tab",), "fields": ("authors", "created_at", "updated_at")}),
    )
    actions = ("publish_selected", "move_to_drafts")
    actions_list = ("publish_all_drafts",)
    actions_row = ("toggle_status",)
    actions_detail = ("open_comments",)
    actions_submit_line = ("save_and_publish",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        queryset = super().get_queryset(request)
        return queryset.annotate(comment_total=Count("comments")).prefetch_related("tags", "comments__author")

    @display(description="Post", ordering="title", header=True)
    def post_header(self, obj: Post) -> list[str]:
        return [obj.title, obj.authors.email]

    @display(description="Status", ordering="status", label={"published": "success", "draft": "warning"})
    def status_label(self, obj: Post) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description="Category", ordering="category__name")
    def category_name(self, obj: Post) -> str:
        return obj.category.name if obj.category else "-"

    @display(description="Tags", dropdown=True)
    def tags_dropdown(self, obj: Post) -> dict:
        tags = obj.tags.all()
        return {
            "title": f"{len(tags)} tags",
            "items": [{"title": tag.name} for tag in tags],
        }

    @display(description="Comments", ordering="comment_total")
    def comment_count(self, obj: Post) -> int:
        return obj.comment_total

    @action(description="Publish selected")
    def publish_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(status=Post.Status.PUBLISHED)

    @action(description="Move to drafts")
    def move_to_drafts(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(status=Post.Status.DRAFT)

    @action(description="Publish all drafts", permissions=["change"])
    def publish_all_drafts(self, request: HttpRequest) -> HttpResponse:
        Post.objects.filter(status=Post.Status.DRAFT).update(status=Post.Status.PUBLISHED)
        return redirect("admin:blog_post_changelist")

    @action(description="Publish / unpublish", permissions=["change"])
    def toggle_status(self, request: HttpRequest, object_id: int) -> HttpResponse:
        post = get_object_or_404(Post, pk=object_id)
        if post.status == Post.Status.PUBLISHED:
            post.status = Post.Status.DRAFT
        else:
            post.status = Post.Status.PUBLISHED
        post.save()
        return redirect("admin:blog_post_changelist")

    @action(description="Open comments")
    def open_comments(self, request: HttpRequest, object_id: int) -> HttpResponse:
        comments_url = reverse("admin:blog_comment_changelist")
        return redirect(f"{comments_url}?post__id__exact={object_id}")

    @action(description="Save & publish", permissions=["change"])
    def save_and_publish(self, request: HttpRequest, obj: Post) -> None:
        obj.status = Post.Status.PUBLISHED
        obj.save()
