from http import HTTPStatus

from api.recipes.serializers import (BookmarkCreateSerializer,
                                     CartItemCreateSerializer,
                                     IngredientSerializer,
                                     RecipeCreateSerializer, RecipeSerializer,
                                     ShortRecipeSerializer, TagSerializer)
from django.conf import settings
from django.db.models import F, Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import Ingredient, IngredientAmount, Recipe, Tag
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.pagination import CustomPageNumberPagination

from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthorOrAdminOrReadOnly


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Отдаёт список тегов (например: Завтрак, Обед, Ужин)."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None


class IngredientViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """Отдаёт список ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """CRUD для рецептов."""

    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags', 'ingredient_amounts__ingredient'
    )
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = [IsAuthorOrAdminOrReadOnly]
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        """Для POST/PUT/PATCH используем отдельный сериализатор."""
        if self.request.method in ('POST', 'PUT', 'PATCH'):
            return RecipeCreateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        serializer.save()

    @action(
        detail=True,
        methods=('get',),
        url_path='get-link',
        permission_classes=(permissions.AllowAny,),
    )
    def get_link(self, request, pk=None):
        """Возвращает ссылку на рецепт."""
        recipe = self.get_object()
        base = (settings.FRONTEND_URL
                or request.build_absolute_uri('/')).rstrip('/')
        url = f'{base}/recipes/{recipe.id}'
        return Response({'short-link': url}, status=HTTPStatus.OK)

    def _toggle_relation(
        self,
        request,
        *,
        serializer_class,
        recipe,
        add: bool,
        already_message: str = '',
        absent_message: str = '',
    ):
        """DRY для избранного и корзины через сериалайзер."""
        if add:
            serializer = serializer_class(
                data={'recipe': recipe.id},
                context={'request': request},
            )
            serializer.is_valid(raise_exception=False)
            if serializer.errors:
                return Response({'detail': already_message},
                                status=status.HTTP_400_BAD_REQUEST)
            try:
                serializer.save()
            except Exception:
                return Response({'detail': already_message},
                                status=status.HTTP_400_BAD_REQUEST)
            data = ShortRecipeSerializer(
                recipe, context={'request': request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        deleted, _ = serializer_class.Meta.model.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted:
            return Response({'detail': absent_message},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        """Добавить рецепт в избранное текущего пользователя."""
        recipe = self.get_object()
        return self._toggle_relation(
            request,
            serializer_class=BookmarkCreateSerializer,
            recipe=recipe,
            add=True,
            already_message='Рецепт уже в избранном',
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        """Удалить рецепт из избранного."""
        recipe = self.get_object()
        return self._toggle_relation(
            request,
            serializer_class=BookmarkCreateSerializer,
            recipe=recipe,
            add=False,
            absent_message='Рецепта нет в избранном',
        )

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
    )
    def shopping_cart(self, request, pk=None):
        """Добавить рецепт в список покупок."""
        recipe = self.get_object()
        return self._toggle_relation(
            request,
            serializer_class=CartItemCreateSerializer,
            recipe=recipe,
            add=True,
            already_message='Рецепт уже в списке покупок',
        )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        """Удалить рецепт из списка покупок."""
        recipe = self.get_object()
        return self._toggle_relation(
            request,
            serializer_class=CartItemCreateSerializer,
            recipe=recipe,
            add=False,
            absent_message='Рецепта нет в списке покупок',
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
        methods=('get',),
        permission_classes=(IsAuthenticated,),
        url_path='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        """Txt-файл со всеми ингредиентами из рецептов в корзине."""
        payload = self._build_shopping_list(request.user)
        response = HttpResponse(
            payload, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response
