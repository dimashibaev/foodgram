from http import HTTPStatus

from django.contrib.auth.password_validation import validate_password
from django.shortcuts import get_object_or_404
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from backend.pagination import CustomPageNumberPagination

from .models import Follow, User
from .serializers import (AvatarUploadSerializer, SubscriptionSerializer,
                          UserRegistrationSerializer, UserSerializer)


class UserViewSet(viewsets.ModelViewSet):
    """
    Вьюсет для работы с пользователями:
    - список, регистрация и профиль,
    - /users/me/ (данные текущего пользователя),
    - смена пароля,
    - загрузка/удаление аватара,
    - подписки и отписки
    """
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('username', 'email', 'first_name', 'last_name')
    pagination_class = CustomPageNumberPagination

    _auth_required = {
        'me', 'avatar', 'avatar_delete', 'subscribe',
        'unsubscribe', 'subscriptions', 'set_password'
    }

    def get_permissions(self):
        """Возвращает права доступа в зависимости от action"""
        if self.action == 'create':
            return [AllowAny()]
        if self.action in self._auth_required:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_serializer_class(self):
        """Возвращает сериализатор в зависимости от action"""
        if self.action == 'create':
            return UserRegistrationSerializer
        if self.action in ('subscriptions', 'subscribe'):
            return SubscriptionSerializer
        if self.action == 'avatar':
            return AvatarUploadSerializer
        return UserSerializer

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        """Возвращает данные текущего пользователя."""
        return Response(
            UserSerializer(request.user, context={'request': request}).data
        )

    @action(
        detail=False,
        methods=['post'],
        url_path='set_password',
        permission_classes=[IsAuthenticated],
    )
    def set_password(self, request):
        """Изменяет пароль текущего пользователя"""
        current_password = (request.data.get('current_password') or '').strip()
        new_password = (request.data.get('new_password') or '').strip()

        if not request.user.check_password(current_password):
            raise serializers.ValidationError(
                {'current_password': 'Неверный текущий пароль.'}
            )

        validate_password(new_password, user=request.user)

        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        return Response(status=HTTPStatus.NO_CONTENT)

    @action(
        detail=False,
        methods=['put', 'patch', 'post'],
        url_path='me/avatar',
        parser_classes=[JSONParser, MultiPartParser, FormParser],
        permission_classes=[IsAuthenticated],
    )
    def avatar(self, request):
        """Загружает или обновляет аватар пользователя"""
        if (
            "avatar" not in request.data
            and "avatar" not in getattr(request, "FILES", {})
        ):
            return Response(
                {"avatar": ["Это поле обязательно."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(
            instance=request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @avatar.mapping.delete
    def avatar_delete(self, request):
        """Удаляет аватар пользователя."""
        if request.user.avatar:
            request.user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk=None):
        """Оформляет подписку на выбранного автора"""
        author = get_object_or_404(User, pk=pk)

        if author == request.user:
            return Response(
                {'detail': 'Нельзя подписаться на самого себя.'},
                status=HTTPStatus.BAD_REQUEST
            )

        if Follow.objects.filter(
                subscriber=request.user, author=author).exists():
            return Response(
                {'detail': 'Вы уже подписаны на этого автора.'},
                status=HTTPStatus.BAD_REQUEST
            )

        Follow.objects.create(subscriber=request.user, author=author)
        data = SubscriptionSerializer(
            author, context={'request': request}).data
        return Response(data, status=HTTPStatus.CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, pk=None):
        """Отписывает текущего пользователя от выбранного автора"""
        author = get_object_or_404(User, pk=pk)
        qs = Follow.objects.filter(subscriber=request.user, author=author)
        if not qs.exists():
            return Response(
                {'detail': 'Подписка на этого автора отсутствует.'},
                status=HTTPStatus.BAD_REQUEST
            )
        qs.delete()
        return Response(status=HTTPStatus.NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        """Возвращает список авторов, на которых подписан пользователь"""
        authors = User.objects.filter(
            subscribers__subscriber=request.user
        ).distinct()
        page = self.paginate_queryset(authors)
        ser = SubscriptionSerializer(
            page if page is not None else authors,
            many=True,
            context={'request': request}
        )
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)
