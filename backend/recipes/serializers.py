from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from backend.const import (MAX_COOKING_TIME, MAX_INGR_AMOUNT,
                           MIN_AMOUNT, MIN_COOKING_TIME)
from recipes.models import Ingredient, IngredientAmount, Recipe, Tag
from users.serializers import UserSerializer


class TagSerializer(serializers.ModelSerializer):
    """Cериализатор тега"""
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class IngredientSerializer(serializers.ModelSerializer):
    """Cериализатор ингредиента"""
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Представление ингредиента внутри рецепта"""
    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = IngredientAmount
        fields = ("id", "name", "measurement_unit", "amount")


class IngredientAmountInputSerializer(serializers.Serializer):
    """
    Ввод ингредиента при создании/обновлении рецепта
    """
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source="ingredient",
    )
    amount = serializers.IntegerField(
        min_value=MIN_AMOUNT, max_value=MAX_INGR_AMOUNT)


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Короткая карточка рецепта (для избранного/корзины и т.п.)"""
    image = serializers.ImageField(source="picture", read_only=True)
    cooking_time = serializers.IntegerField(source="duration", read_only=True)

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class RecipeSerializer(serializers.ModelSerializer):
    """Детальная карточка рецепта"""
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientAmountSerializer(
        source="ingredient_amounts", many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    text = serializers.CharField(source="description", read_only=True)
    image = serializers.ImageField(source="picture", read_only=True)
    cooking_time = serializers.IntegerField(source="duration", read_only=True)

    class Meta:
        model = Recipe
        fields = (
            "id", "name", "author", "ingredients", "tags",
            "is_favorited", "is_in_shopping_cart",
            "text", "image", "cooking_time",
        )

    def get_is_favorited(self, obj):
        user = self.context.get("request").user
        if not user or user.is_anonymous:
            return False
        return user.bookmarks.filter(recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get("request").user
        if not user or user.is_anonymous:
            return False
        return user.cart_items.filter(recipe=obj).exists()


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Создание / обновление рецепта"""
    ingredients = IngredientAmountInputSerializer(many=True, required=False)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False
    )
    image = Base64ImageField(source="picture", required=False)
    text = serializers.CharField(source="description", required=False)
    cooking_time = serializers.IntegerField(source="duration",
                                            min_value=MIN_COOKING_TIME,
                                            max_value=MAX_COOKING_TIME,
                                            required=False)
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Recipe
        fields = (
            "name", "image", "text", "cooking_time",
            "ingredients", "tags", "author",
        )

    def validate_ingredients(self, ingredients):
        """Проверяем список ингредиентов: не пустой, без дублей"""
        if ingredients is None:
            return ingredients
        if not ingredients:
            raise ValidationError("Нужно добавить хотя бы один ингредиент.")
        ids = [item["ingredient"].id for item in ingredients]
        if len(ids) != len(set(ids)):
            raise ValidationError("Ингредиенты должны быть уникальными.")
        for it in ingredients:
            amt = it.get("amount")
            if amt is None or not (MIN_AMOUNT <= int(amt) <= MAX_INGR_AMOUNT):
                raise ValidationError(
                    f"Количество для ингредиента должно быть"
                    f"в диапазоне {MIN_AMOUNT}…{MAX_INGR_AMOUNT}."
                )
        return ingredients

    def validate_tags(self, tags):
        """Запрещаем повторяющиеся теги в запросе"""
        if tags is None:
            return tags
        if not tags:
            raise serializers.ValidationError("Выберите минимум один тег.")

        ids = [t.id for t in tags]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Теги должны быть уникальными.")
        return tags

    def validate(self, attrs):
        is_create = self.instance is None
        data = self.initial_data

        if is_create:
            required = ["name", "description", "duration",
                        "picture", "ingredients", "tags"]
            missing = [f for f in required if f not in attrs and f not in data]
            if missing:
                raise ValidationError(
                    {self._out_key(k): "Обязательное поле." for k in missing})

        if "image" in data or "picture" in data:
            val = data.get("image", data.get("picture"))
            if val in ("", None, []):
                raise ValidationError({"image": "Изображение обязательно."})

        if not is_create:
            if "ingredients" not in data:
                raise ValidationError(
                    {"ingredients": "Нужно добавить хотя бы один ингредиент."})
            if "tags" not in data:
                raise ValidationError({"tags": "Выберите минимум один тег."})

        duration = attrs.get("duration")
        if (
            duration is not None
            and not (MIN_COOKING_TIME <= duration <= MAX_COOKING_TIME)
        ):
            raise ValidationError(
                {"cooking_time": f"1…{MAX_COOKING_TIME} минут."})

        return attrs

    def _out_key(self, internal):
        """Преобразование внутренних имён в ключи ответа под фронт."""
        return {
            "description": "text",
            "duration": "cooking_time",
            "picture": "image",
        }.get(internal, internal)

    def create(self, validated_data):
        """Создание рецепта"""
        ingredients_data = validated_data.pop("ingredients")
        tags_data = validated_data.pop("tags")
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        IngredientAmount.objects.bulk_create([
            IngredientAmount(
                recipe=recipe,
                ingredient=item["ingredient"],
                amount=item["amount"],
            )
            for item in ingredients_data
        ])
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта"""
        ingredients_data = validated_data.pop("ingredients", None)
        tags_data = validated_data.pop("tags", None)

        for field in ("name", "description", "duration", "picture"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            instance.ingredient_amounts.all().delete()
            IngredientAmount.objects.bulk_create([
                IngredientAmount(
                    recipe=instance,
                    ingredient=item["ingredient"],
                    amount=item["amount"],
                )
                for item in ingredients_data
            ])

        instance.save()
        return instance

    def to_representation(self, instance):
        """После create/update отдаём полную карточку, как на GET"""
        return RecipeSerializer(instance, context=self.context).data
