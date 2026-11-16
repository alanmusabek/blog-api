# Imports
# Other imports
from typing import Any
from faker import Faker
from datetime import datetime, timedelta
from random import choice, random, randint, sample

# Django imports
from django.core.management.base import BaseCommand, CommandParser, CommandError
from django.contrib.auth.hashers import make_password
from django.utils.text import slugify
from django.utils import timezone

# Model imports
from apps.auths.models import User
from apps.blog.models import Category, Tag, Post, Comment

fake = Faker()
# DEFAULTS
DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500
SEED_PASSWORD = "password123"

# PROBABILITIES
STAFF_SHARE = 0.2
INACTIVE_SHARE = 0.1
NO_CATEGORY_SHARE = 0.1
PUBLISHED_SHARE = 0.7
MAX_TAGS_PER_POST = 5

# POST CONTENT
TITLE_WORDS = 6
BODY_PARAGRAPHS = 3
COMMENT_SENTENCES = 3
SLUG_BASE_MAX_LENGTH = 240
PARAGRAPH_SEPARATOR = "\n\n"

# CATEGORIES and TAGS
CATEGORIES = [
    "Python",
    "Django",
    "JavaScript",
    "Machine Learning",
    "DevOps",
    "Databases",
    "Web Development",
    "Software Engineering",
]

TAGS = [
    "beginner",
    "advanced",
    "tutorial",
    "programming",
    "backend",
    "frontend",
    "python",
    "django",
    "database",
    "api",
    "testing",
    "deployment",
    "security",
    "performance",
    "architecture",
    "learning",
    "guide",
    "tips",
    "open-source",
    "development",
]

MAILBOX_DOMAINS = [
    "@gmail.com",
    "@outlook.com",
    "@yahoo.com",
]

# Dates
DAYS_BACK = 365
SECONDS_IN_DAY = 24 * 60 * 60
EDITED_SHARE = 0.3
MIN_EDIT_DAYS = 1
MAX_EDIT_DAYS = 30

# Custom functions
def random_past_datetime(now: datetime) -> datetime:
    """Random time in the last 365 days"""
    return now - timedelta(seconds=randint(0, DAYS_BACK * SECONDS_IN_DAY))

def random_updated_at(created_at: datetime, now: datetime) -> datetime:
    """30% of posts edited after ~30 days"""
    if random() >= EDITED_SHARE:
        return created_at
    edited_at = created_at + timedelta(days=randint(MIN_EDIT_DAYS, MAX_EDIT_DAYS))
    return min(edited_at, now)

def random_datetime_between(start: datetime, end: datetime) -> datetime:
    """Random time between start and end"""
    return start + (end - start) * random()
# Command class
class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--users", type=int, default=DEFAULT_USERS, help="Number of users to create")
        parser.add_argument("--posts", type=int, default=DEFAULT_POSTS, help="Number of posts to create")
        parser.add_argument("--comments", type=int, default=DEFAULT_COMMENTS, help="Number of comments to create")
        parser.add_argument("--clear", action="store_true", help="Delete existing data before seeding")


    def __get_email_from_full_name(self, first_name: str, fake_last_name: str, existing_emails: set) -> str:
        """Get email from full name.Temirbolat MAratuly -> temirbolat.maratuly"""
        
        full_name = f"{slugify(first_name)}.{slugify(fake_last_name)}"
        
        domain = choice(MAILBOX_DOMAINS)
        email = f"{full_name}{domain}"
        counter = 1
        while email in existing_emails:
            email = f"{full_name}{counter}{domain}"
            counter += 1
        existing_emails.add(email)
        return email 

    def __create_users(self, number_of_users: int) -> None:
        users = []
        hashed_password = make_password(SEED_PASSWORD)
        existing_emails = set(User.objects.values_list("email", flat=True))

        for i in range(number_of_users):
            fake_first_name = fake.first_name()
            fake_last_name = fake.last_name()
            generated_email = self.__get_email_from_full_name(fake_first_name, fake_last_name, existing_emails)

            users.append(
                User(
                    email= generated_email,
                    first_name = fake_first_name,
                    second_name = fake_last_name,
                    password=f"{hashed_password}",
                    is_staff=random() < STAFF_SHARE,
                    is_active=random() >= INACTIVE_SHARE
                )
            )
        User.objects.bulk_create(users)
        return len(users)

    def __create_categories(self) -> int:
        categories = []
        existing_names = set(Category.objects.values_list("name", flat=True))
        existing_slugs = set(Category.objects.values_list("slug", flat=True))
        for name in CATEGORIES:
            if name in existing_names: 
                continue
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while slug in existing_slugs:
                slug = f"{base_slug}-{counter}"
                counter += 1
            existing_slugs.add(slug)
            categories.append(
                Category(
                    name = name,
                    slug = slug
                )
            )
        Category.objects.bulk_create(categories)
        return len(categories)

    def __create_tags(self) -> int:
        tags = []

        existing_names = set(Tag.objects.values_list("name", flat=True))
        existing_slugs = set(Tag.objects.values_list("slug", flat=True))

        for name in TAGS:
            if name in existing_names: 
                continue
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while slug in existing_slugs:
                slug = f"{base_slug}-{counter}"
                counter += 1
            existing_slugs.add(slug)
            tags.append(
                Tag(
                    name = name,
                    slug = slug
                )
            )
        Tag.objects.bulk_create(tags, ignore_conflicts= True)
        return len(tags)

    def __unique_post_slug(self, title: str, existing_slugs: set[str]) -> str:
        """Slug from the title, with a number at the end if it is already taken"""
        base_slug = slugify(title)[:SLUG_BASE_MAX_LENGTH]
        slug = base_slug
        counter = 1
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1
        existing_slugs.add(slug)
        return slug

    def __create_posts(self, number_of_posts: int, users: list[User]) -> list[Post]:
        posts = []
        post_tags = []
        categories = list(Category.objects.all())
        tags = list(Tag.objects.all())
        existing_slugs = set(Post.objects.values_list("slug", flat=True))

        for _ in range(number_of_posts):
            title = fake.sentence(nb_words=TITLE_WORDS).rstrip(".")
            category = (choice(categories) if categories and random() >= NO_CATEGORY_SHARE else None)
            posts.append(Post(
                title=title,
                slug=self.__unique_post_slug(title, existing_slugs),
                body=PARAGRAPH_SEPARATOR.join(fake.paragraphs(nb=BODY_PARAGRAPHS)),
                authors=choice(users),
                category=category,
                status=(Post.Status.PUBLISHED if random()< PUBLISHED_SHARE else Post.Status.DRAFT)
                )
            )
            selected_tags = sample(tags, k=randint(0, min(MAX_TAGS_PER_POST, len(tags))))
            post_tags.append(selected_tags)
        created_posts = Post.objects.bulk_create(posts)

        # Date
        now = timezone.now()
        for post in created_posts:

            post.created_at = random_past_datetime(now)
            post.updated_at = random_updated_at(post.created_at, now)
        Post.objects.bulk_update(created_posts, ["created_at", "updated_at"])


        PostTag = Post.tags.through
        PostTag.objects.bulk_create([
            PostTag(post_id=post.pk, tag_id=tag.pk)
            for post, selected_tags in zip(created_posts, post_tags)
            for tag in selected_tags
        ])
        return created_posts

    def __create_comments(self, number_of_comments: int, users: list[User], posts: list[Post]) -> int:
        comments = []

        published_posts = [post for post in posts if post.status == Post.Status.PUBLISHED]

        if number_of_comments > 0 and not published_posts:
            raise CommandError(
                "Cannot create comments without published posts."
            )

        for _ in range(number_of_comments):
            comments.append(
                Comment(
                    post=choice(published_posts),
                    author=choice(users),
                    body=fake.paragraph(nb_sentences=COMMENT_SENTENCES)
                )
            )

        created_comments = Comment.objects.bulk_create(comments)
        now = timezone.now()
        for comment in created_comments:
            comment.created_at = random_datetime_between(comment.post.created_at, now)
        Comment.objects.bulk_update(created_comments, ["created_at"])
        return len(created_comments)
        
    def handle(self, *args: Any, **options: Any) -> None:
        start_time: datetime = datetime.now()

        #counts
        users_count: int = options["users"]
        posts_count: int = options["posts"]
        comments_count: int = options["comments"]
        clear: bool = options["clear"]

        if min(users_count, posts_count, comments_count) < 0:
            raise CommandError("Counts cannot be negative.")
        
        if clear:
            self.stdout.write(f"Clearing has started...")
            Comment.objects.all().delete()
            Post.objects.all().delete()
            Tag.objects.all().delete()
            Category.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(f"Cleared successfully!")

        users_created = self.__create_users(users_count)
        users = list(User.objects.all())
        
        if (posts_count > 0 or comments_count > 0) and not users:
            raise CommandError("No users available")
        categories_created = self.__create_categories()
        tags_created = self.__create_tags()
        posts = self.__create_posts(posts_count, users)
        posts_created = len(posts)
        comments_created = self.__create_comments(comments_count, users, posts)

        elapsed_time = (datetime.now() - start_time).total_seconds()
        self.stdout.write(self.style.SUCCESS("Seeding completed!"))
        self.stdout.write(f"Categories: {categories_created}")
        self.stdout.write(f"Tags: {tags_created}")
        self.stdout.write(f"Posts: {posts_created}")
        self.stdout.write(f"Comments: {comments_created}")
        self.stdout.write(f"Time: {elapsed_time:.2f} seconds")





