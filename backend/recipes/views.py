import json
from http import HTTPStatus

from django.conf import settings
from django.db.models import F, Sum
from django.http import HttpResponse
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from backend.pagination import CustomPageNumberPagination

from .filters import RecipeFilter
from .models import (Bookmark, CartItem, Ingredient, IngredientAmount, Recipe,
                     Tag)
from .permissions import IsAuthorOrAdminOrReadOnly
from .serializers import (IngredientSerializer, RecipeCreateSerializer,
                          RecipeSerializer, ShortRecipeSerializer,
                          TagSerializer)


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
    """
    Отдаёт список ингредиентов.
    Есть поиск по имени (?name=ябл).
    """
    queryset = Ingredient.objects.all().order_by('name')
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    def get_queryset(self):
        """
        Если передан ?name=, возвращает до 10 ингредиентов,
        у которых название содержит подстроку.
        """
        qs = super().get_queryset()
        q = self.request.query_params.get('name')
        if q is None or q == '':
            return qs
        # ВАЖНО: начало строки, регистронезависимо
        return qs.filter(name__istartswith=q).order_by('name')[:10] 


class RecipeViewSet(viewsets.ModelViewSet):
    """
    CRUD для рецептов.
    Автор может изменять свои рецепты блюд, админ — любые.
    """
    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags', 'ingredient_amounts__ingredient'
    )
    filterset_class = RecipeFilter
    permission_classes = [IsAuthorOrAdminOrReadOnly]
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        """Для POST/PUT/PATCH используем отдельный сериализатор (с валидацией)."""
        if self.request.method in ('POST', 'PUT', 'PATCH'):
            return RecipeCreateSerializer
        return RecipeSerializer

    def _coerce_nested(self, data):
        """
        Вспомогательный метод:
        превращает JSON-строки в списки/словарь для multipart-запросов.
        Например: ingredients="[{'id': 1, 'amount': 2}]"
        """
        m = data.copy()
        for key in ('ingredients', 'tags'):
            val = m.get(key)
            if isinstance(val, str):
                try:
                    m[key] = json.loads(val)
                except json.JSONDecodeError:
                    pass
        return m

    def perform_create(self, serializer):
        """
        При создании рецепта всегда сохраняем автора = текущий пользователь.
        """
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Создание рецепта.
        """
        data = self._coerce_nested(request.data)
        serializer = self.get_serializer(
            data=data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read = RecipeSerializer(serializer.instance,
                              context=self.get_serializer_context())
        return Response(read.data, status=HTTPStatus.CREATED)

    def update(self, request, *args, **kwargs):
        """
        Обновление рецепта (PUT/PATCH).
        """
        instance = self.get_object()
        data = self._coerce_nested(request.data)
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(
            instance, data=data, partial=partial, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        read = RecipeSerializer(serializer.instance,
                              context=self.get_serializer_context())
        return Response(read.data, status=HTTPStatus.OK)

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
        base = (getattr(settings, 'FRONTEND_URL', '')
                or request.build_absolute_uri('/')).rstrip('/')
        url = f"{base}/recipes/{recipe.id}/"
        return Response({'short-link': url}, status=HTTPStatus.OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """
        Добавить рецепт в избранное текущего пользователя.
        """
        recipe = self.get_object()
        obj, created = Bookmark.objects.get_or_create(
            user=request.user, recipe=recipe)
        if not created:
            return Response({'detail': 'Рецепт уже в избранном'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ShortRecipeSerializer(recipe, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        """
        Удалить рецепт из избранного.
        """
        recipe = self.get_object()
        deleted, _ = Bookmark.objects.filter(
            user=request.user, recipe=recipe).delete()
        if not deleted:
            return Response({'detail': 'Рецепта нет в избранном'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """
        Добавить рецепт в список покупок.
        """
        recipe = self.get_object()
        obj, created = CartItem.objects.get_or_create(
            user=request.user, recipe=recipe)
        if not created:
            return Response({'detail': 'Рецепт уже в списке покупок'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ShortRecipeSerializer(recipe, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        """
        Удалить рецепт из списка покупок.
        """
        recipe = self.get_object()
        deleted, _ = CartItem.objects.filter(
            user=request.user, recipe=recipe).delete()
        if not deleted:
            return Response({'detail': 'Рецепта нет в списке покупок'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

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
        items = (
            IngredientAmount.objects
            .filter(recipe__cart_items__user=request.user)
            .values(
                name=F('ingredient__name'),
                unit=F('ingredient__measurement_unit'),
            )
            .annotate(total=Sum('amount'))
            .order_by('name')
        )

        lines = [f"{it['name']} — {it['total']} {it['unit']}" for it in items]
        content = '\n'.join(lines) or 'Список покупок пуст.'

        resp = HttpResponse(content, content_type='text/plain; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return resp
