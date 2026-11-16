from django.db import migrations, models


def fill_post_slugs(apps, schema_editor):
    """Give every existing post a unique slug before the column becomes unique."""
    Post = apps.get_model("blog", "Post")
    posts = list(Post.objects.only("pk"))
    for post in posts:
        post.slug = f"post-{post.pk}"
    Post.objects.bulk_update(posts, ["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0002_comment"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="body",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="post",
            name="slug",
            field=models.SlugField(max_length=255, null=True),
        ),
        migrations.RunPython(fill_post_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="post",
            name="slug",
            field=models.SlugField(max_length=255, unique=True),
        ),
    ]
