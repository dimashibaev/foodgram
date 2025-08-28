from django.contrib import admin

from .models import (
    Bookmark, CartItem, Ingredient,
    IngredientAmount, Recipe, Tag
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")
    ordering = ("id",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "measurement_unit")
    search_fields = ("name",)
    ordering = ("name",)


class IngredientAmountInline(admin.TabularInline):
    model = IngredientAmount
    extra = 1
    autocomplete_fields = ("ingredient",)
    min_num = 0


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "author", "created_at")
    list_filter = ("tags", "author")
    search_fields = ("name", "author__username", "author__email")
    ordering = ("-created_at",)
    filter_horizontal = ("tags",)
    inlines = (IngredientAmountInline,)

    fieldsets = (
        (None, {
            "fields": ("name", "author", "description", "picture", "duration")
        }),
        ("Классификация", {
            "fields": ("tags",),
        }),
    )


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe")
    search_fields = ("user__username", "recipe__name")
    list_filter = ("user",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe")
    search_fields = ("user__username", "recipe__name")
    list_filter = ("user",)
