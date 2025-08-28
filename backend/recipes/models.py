from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import CheckConstraint, Q

from backend.const import (MAX_COOKING_TIME, MAX_INGR_AMOUNT,
                           MIN_AMOUNT, MIN_COOKING_TIME)


class Tag(models.Model):
    """Модель тега"""
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель ингридиента"""
    name = models.CharField(max_length=200)
    measurement_unit = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    """Модель рецепта"""
    name = models.CharField(max_length=200)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='recipes',
        on_delete=models.CASCADE
    )
    description = models.TextField(verbose_name="Описание")
    picture = models.ImageField(
        upload_to='recipes/images/',
        verbose_name="Изображение"
    )
    duration = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_COOKING_TIME,
                              message="Время приготовления должно быть ≥ 1"
                              ),
            MaxValueValidator(
                MAX_COOKING_TIME,
                message=f"Время приготовления не более {MAX_COOKING_TIME} мин."
            ),
        ],
        verbose_name="Время приготовления (мин.)"
    )
    tags = models.ManyToManyField(
        Tag, related_name='recipes', verbose_name="Теги")
    ingredients = models.ManyToManyField(
        'Ingredient',
        through='IngredientAmount',
        related_name='recipes',
        verbose_name="Ингредиенты"
    )

    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name="Опубликовано")

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        ordering = ('-created_at',)

    def __str__(self):
        return self.name


class IngredientAmount(models.Model):
    """Количество конкретного ингредиента в рецепте"""
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_amounts'
    )
    amount = models.PositiveIntegerField(
        validators=[
            MinValueValidator(
                MIN_AMOUNT,
                message="Количество должно быть не менее 1"
            ),
            MaxValueValidator(
                MAX_INGR_AMOUNT,
                message=f"Количество не больше {MAX_INGR_AMOUNT}"
            ),
        ]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]
        CheckConstraint(
            check=Q(amount__gte=MIN_AMOUNT, amount__lte=MAX_INGR_AMOUNT),
            name="ingredient_amount_range_check",
        ),
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецептах"

    def __str__(self):
        return f"{self.ingredient.name} × {self.amount} для {self.recipe.name}"


class Bookmark(models.Model):
    """Модель избранного"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='bookmarks',
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe, related_name='bookmarks', on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'], name='unique_user_recipe_favorite')
        ]
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"

    def __str__(self):
        return f"{self.user} -> {self.recipe}"


class CartItem(models.Model):
    """Модель покупки"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='cart_items',
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe, related_name='cart_items', on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'], name='unique_user_recipe_cart')
        ]
        verbose_name = "Покупка"
        verbose_name_plural = "Покупки"

    def __str__(self):
        return f"{self.user} -> {self.recipe}"
