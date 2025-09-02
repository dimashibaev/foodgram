from django.contrib import admin
from recipes.models import (Bookmark, CartItem, Ingredient, IngredientAmount,
                            Recipe, Tag)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'id')
    list_display_links = ('slug', 'name')
    search_fields = ('name', 'slug')
    ordering = ('slug',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit', 'id')
    list_display_links = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


class IngredientAmountInline(admin.TabularInline):
    model = IngredientAmount
    extra = 1
    autocomplete_fields = ('ingredient',)
    min_num = 0


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'created_at', 'id')
    list_display_links = ('name', 'author')
    list_filter = ('author', 'tags')
    search_fields = ('name',)
    ordering = ('-created_at',)
    filter_horizontal = ('tags',)
    inlines = (IngredientAmountInline,)
    date_hierarchy = 'created_at'
    list_select_related = ('author',)
    raw_id_fields = ('author',)

    fieldsets = (
        (None, {
            'fields': ('name', 'author', 'text', 'image', 'cooking_time'),
        }),
        ('Классификация', {
            'fields': ('tags',),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('author').prefetch_related(
            'tags',
            'ingredient_amounts__ingredient',
        )


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'id')
    list_display_links = ('user', 'recipe')
    list_filter = ('user',)
    search_fields = ('recipe__name',)
    ordering = ('id',)
    list_select_related = ('user', 'recipe')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'recipe')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'id')
    list_display_links = ('user', 'recipe')
    list_filter = ('user',)
    search_fields = ('recipe__name',)
    ordering = ('id',)
    list_select_related = ('user', 'recipe')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'recipe')
