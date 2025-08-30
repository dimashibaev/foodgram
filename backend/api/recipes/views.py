from http import HTTPStatus

from api.recipes.serializers import (IngredientSerializer,
                                     RecipeCreateSerializer, RecipeSerializer,
                                     ShortRecipeSerializer, TagSerializer)
from django.conf import settings
from django.db.models import F, Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import (Bookmark, CartItem, Ingredient, IngredientAmount,
                            Recipe, Tag)
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.pagination import CustomPageNumberPagination

from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthorOrAdminOrReadOnly


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Отдаёт список тегов (например: Завтрак, Обед, Ужин).
    Только для чтения.
    """
    queryset = Tag.objects.all().order_by('id')
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None


class IngredientViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """Отдаёт список ингредиентов."""
    queryset = Ingredient.objects.all().order_by('name')
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """
    CRUD для рецептов.
    Автор может изменять свои рецепты блюд, админ — любые.
    """
    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags', 'ingredient_amounts__ingredient'
    )
    serializer_class = RecipeSerializer
    filterset_class = RecipeFilter
    permission_classes = [IsAuthorOrAdminOrReadOnly]
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        """Для POST/PUT/PATCH используем отдельный сериализатор"""
        if self.request.method in ('POST', 'PUT', 'PATCH'):
            return RecipeCreateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        """
        При создании рецепта всегда сохраняем автора = текущий пользователь.
        """
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        serializer.save()

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link',
        permission_classes=[permissions.AllowAny],
    )
    def get_link(self, request, pk=None):
        """
        Возвращает ссылку на рецепт (использует FRONTEND_URL из настроек).
        """
        recipe = self.get_object()
        base = getattr(settings, 'FRONTEND_URL', '').rstrip('/')
        if not base:
            base = request.build_absolute_uri('/').rstrip('/')
        url = f"{base}/recipes/{recipe.id}"
        return Response({'short-link': url}, status=HTTPStatus.OK)

    def _toggle_relation(self, request, model, recipe, *, add: bool,
                         already_msg: str = '', absent_msg: str = ''):
        """ DRY для избранного и корзины """
        if add:
            obj, created = model.objects.get_or_create(
                user=request.user, recipe=recipe)
            if not created:
                return Response({'detail': already_msg},
                                status=status.HTTP_400_BAD_REQUEST)
            data = ShortRecipeSerializer(
                recipe, context={'request': request}).data
            return Response(data, status=status.HTTP_201_CREATED)
        deleted, _ = model.objects.filter(
            user=request.user, recipe=recipe).delete()
        if not deleted:
            return Response({'detail': absent_msg},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['post'],
            permission_classes=[IsAuthenticated]
            )
    def favorite(self, request, pk=None):
        """
        Добавить рецепт в избранное текущего пользователя.
        """
        recipe = self.get_object()
        return self._toggle_relation(
            request, Bookmark, recipe,
            add=True,
            already_msg='Рецепт уже в избранном',
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        """
        Удалить рецепт из избранного.
        """
        recipe = self.get_object()
        return self._toggle_relation(
            request, Bookmark, recipe,
            add=False,
            absent_msg='Рецепта нет в избранном',
        )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        """
        Добавить рецепт в список покупок.
        """
        recipe = self.get_object()
        return self._toggle_relation(
            request, CartItem, recipe,
            add=True,
            already_msg='Рецепт уже в списке покупок',
        )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        """
        Удалить рецепт из списка покупок.
        """
        recipe = self.get_object()
        return self._toggle_relation(
            request, CartItem, recipe,
            add=False,
            absent_msg='Рецепта нет в списке покупок',
        )

    def _build_shopping_list(self, user) -> bytes:
        items = (
            IngredientAmount.objects
            .filter(recipe__cart_items__user=user)
            .values(
                name=F('ingredient__name'),
                unit=F('ingredient__measurement_unit'),
            )
            .annotate(total=Sum('amount'))
            .order_by('name')
        )
        lines = [f"{it['name']} — {it['total']} {it['unit']}" for it in items]
        content = '\n'.join(lines) or 'Список покупок пуст.'
        return content.encode('utf-8')

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        """
        Собирает все ингредиенты из рецептов в корзине пользователя,
        суммирует по названию + единице измерения и отдает txt-файл.
        """
        payload = self._build_shopping_list(request.user)
        resp = HttpResponse(payload, content_type='text/plain; charset=utf-8')
        resp['Content-Disposition'] = 'attachment;filename="shopping_list.txt"'
        return resp
