from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from backend.const import (USER_EMAIL_MAX_LEN, USER_FIRST_NAME_MAX_LEN,
                           USER_LAST_NAME_MAX_LEN, USER_USERNAME_MAX_LEN)


class User(AbstractUser):
    """Кастомная модель пользователя."""

    email = models.EmailField(
        'Email',
        max_length=USER_EMAIL_MAX_LEN,
        unique=True,
    )
    first_name = models.CharField(
        'Имя',
        max_length=USER_FIRST_NAME_MAX_LEN,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=USER_LAST_NAME_MAX_LEN,
    )
    username = models.CharField(
        'Имя пользователя',
        max_length=USER_USERNAME_MAX_LEN,
        unique=True,
        validators=[UnicodeUsernameValidator()],
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/avatars/',
        blank=True,
    )


class Follow(models.Model):
    """Модель подписки пользователя на автора рецептов."""

    subscriber = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Автор',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['subscriber', 'author'],
                name='unique_follow',
            ),
        ]
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.subscriber} -> {self.author}'
