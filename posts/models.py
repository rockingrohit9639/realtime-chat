from django.db import models
from account.models import Account
from datetime import datetime
from django.template.defaultfilters import slugify
from django.contrib.contenttypes.fields import GenericRelation
from django.db.models.signals import post_save
from django.dispatch import receiver

from notification.models import Notification

feelings = (
    ("Sad", "Sad"),
    ("Happy", "Happy"),
    ("None", "None")
)


class Post(models.Model):
    author = models.ForeignKey(Account, on_delete=models.CASCADE)
    slug = models.SlugField(max_length=50, blank=True, unique=True)
    post_image = models.ImageField(blank=True, null=True, upload_to="posts/")
    content = models.TextField()
    feeling = models.CharField(max_length=10, choices=feelings, default="None")
    liked = models.ManyToManyField(Account, blank=True, related_name='likes')
    published_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.author.username) + self.content[:30]

    def save(self, **kwargs):
        super(Post, self).save()
        cur_time = datetime.now()
        self.slug = '%s-%d%d%d%d%d%d' % (
            slugify(self.content[:20]), cur_time.hour, cur_time.minute, cur_time.second, cur_time.day, cur_time.month,
            cur_time.year
        )
        super(Post, self).save()

    def get_num_likes(self):
        return self.liked.all().count()


LIKE_CHOICES = (
    ('Like', 'Like'),
    ('Unlike', 'Unlike'),
)


class Like(models.Model):
    author = models.ForeignKey(Account, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    value = models.CharField(choices=LIKE_CHOICES, default="Like", max_length=8)

    notifications = GenericRelation(Notification)
    timestamp = models.DateTimeField(default=datetime.now())

    def __str__(self):
        return self.author.username + self.post.content[:20]

    @property
    def get_cname(self):
        return "Like"


class Comment(models.Model):
    author = models.ForeignKey(Account, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)

    comment = models.CharField(max_length=255, null=False, blank=False)

    notifications = GenericRelation(Notification)
    timestamp = models.DateTimeField(default=datetime.now())

    def __str__(self):
        return self.comment[:20] + " by " + self.author.username

    @property
    def get_cname(self):
        return "Comment"


@receiver(post_save, sender=Like)
def generate_notification(sender, instance, created, **kwargs):
    if created:
        instance.notifications.create(
            target=instance.post.author,
            from_user=instance.author,
            redirect_url="http://localhost:8000/" + "#" + str(instance.post.id),
            statement=f"{instance.author.username} liked your post.",
            content_type=instance,
        )


@receiver(post_save, sender=Comment)
def generate_comment_notification(sender, instance, created, **kwargs):
    if created:
        instance.notifications.create(
            target=instance.post.author,
            from_user=instance.author,
            redirect_url="http://localhost:8000/" + "#" + str(instance.post.id),
            statement=f"{instance.author.username} commented on your post.",
            content_type=instance,
            timestamp=instance.timestamp
        )

