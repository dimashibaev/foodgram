from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import UniqueConstraint

from backend.const import (INGREDIENT_NAME_MAX_LEN, INGREDIENT_UNIT_MAX_LEN,
                           MAX_COOKING_TIME, MAX_INGREDIENT_AMOUNT, MIN_AMOUNT,
                           MIN_COOKING_TIME, RECIPE_NAME_MAX_LEN,
                           TAG_NAME_MAX_LEN, TAG_SLUG_MAX_LEN)


class Tag(models.Model):
    """Модель тега."""

    name = models.CharField(max_length=TAG_NAME_MAX_LEN, unique=True)
    slug = models.SlugField(max_length=TAG_SLUG_MAX_LEN, unique=True)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель ингридиента."""

    name = models.CharField(max_length=INGREDIENT_NAME_MAX_LEN)
    measurement_unit = models.CharField(max_length=INGREDIENT_UNIT_MAX_LEN)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'


class Recipe(models.Model):
    """Модель рецепта."""

    name = models.CharField(max_length=RECIPE_NAME_MAX_LEN)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='recipes',
        on_delete=models.CASCADE
    )
    text = models.TextField(verbose_name='Описание')
    image = models.ImageField(
        upload_to='recipes/images/',
        verbose_name='Изображение'
    )
    cooking_time = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(
                MIN_COOKING_TIME,
                message='Время приготовления должно быть ≥ 1'
            ),
            MaxValueValidator(
                MAX_COOKING_TIME,
                message=f'Время приготовления не более {MAX_COOKING_TIME} мин.'
            ),
        ],
        verbose_name='Время приготовления (мин.)'
    )
    tags = models.ManyToManyField(
        Tag, related_name='recipes', verbose_name='Теги')
    ingredients = models.ManyToManyField(
        'Ingredient',
        through='IngredientAmount',
        related_name='recipes',
        verbose_name='Ингредиенты'
    )

    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name='Опубликовано'
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-created_at',)

    def __str__(self):
        return self.name


class IngredientAmount(models.Model):
    """Количество конкретного ингредиента в рецепте."""
    
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_amounts',
        verbose_name='Рецепт',
    )
    amount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(
                MIN_AMOUNT,
                message='Количество должно быть не менее 1'
            ),
            MaxValueValidator(
                MAX_INGREDIENT_AMOUNT,
                message=f'Количество не больше {MAX_INGREDIENT_AMOUNT}'
            ),
        ]
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient',
            ),
        ]
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'

    def __str__(self):
        return f'{self.ingredient.name} × {self.amount} для {self.recipe.name}'


class UserRecipeLinkBase(models.Model):
    """Абстрактная базовая модель для связок user<->recipe."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        abstract = True


class Bookmark(UserRecipeLinkBase):
    """Модель избранного."""

    class Meta:
        constraints = [
            UniqueConstraint(fields=['user', 'recipe'],
                             name='unique_user_recipe_favorite'),
        ]
        default_related_name = 'bookmarks'
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        return f'{self.user} -> {self.recipe}'


class CartItem(UserRecipeLinkBase):
    """Модель покупки/корзины."""

    class Meta:
        constraints = [
            UniqueConstraint(fields=['user', 'recipe'],
                             name='unique_user_recipe_cart'),
        ]
        default_related_name = 'cart_items'
        verbose_name = 'Покупка'
        verbose_name_plural = 'Покупки'

    def __str__(self):
        return f'{self.user} -> {self.recipe}'