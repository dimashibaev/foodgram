from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models


class User(AbstractUser):
    """Кастомная модель пользователя."""
    email = models.EmailField(
        max_length=150,
        unique=True
    )
    
    first_name = models.CharField(
        'Имя',
        max_length=150,
        blank=False,
    )

    last_name = models.CharField(
        'Фамилия',
        max_length=150,
        blank=False,
    )

    username = models.CharField(
        'Имя пользователя',
        max_length=150,
        unique=True,
        validators=[UnicodeUsernameValidator()]
    )

    avatar = models.ImageField(
        upload_to='users/avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар'
    )


class Follow(models.Model):
    """Модель подписки пользователя на автора рецептов."""
    subscriber = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='subscriptions',
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='subscribers',
        on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['subscriber', 'author'], name='unique_follow')
        ]
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

    def __str__(self):
        return f"{self.subscriber} -> {self.author}"
