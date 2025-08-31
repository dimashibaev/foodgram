import imghdr

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from drf_extra_fields.fields import Base64ImageField
from recipes.models import Recipe
from rest_framework import serializers
from users.models import Follow

from backend.constants import MAX_PHOTO_SIZE_BYTES

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения информации о пользователе."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(
        read_only=True, allow_null=True, required=False)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name', 'avatar', 'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        """Проверяет, подписан ли текущий пользователь на данного автора."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or user.is_anonymous or user == obj:
            return False
        return user.subscriptions.filter(author=obj).exists()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации нового пользователя."""

    password = serializers.CharField(
        write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username',
            'first_name', 'last_name', 'password',
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        """Создаёт нового пользователя с хешированным паролем."""
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password'],
        )
        return user


class SubscriptionSerializer(UserSerializer):
    """Сериализатор для отображения информации о подписке."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count',)

    def get_recipes(self, obj):
        """Возвращает список рецептов автора."""
        from api.recipes.serializers import ShortRecipeSerializer

        qs = Recipe.objects.filter(author=obj)
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit') if request else None
        if isinstance(limit, str) and limit.isdigit():
            n = int(limit)
            if n >= 0:
                qs = qs[:n]

        return ShortRecipeSerializer(
            qs, many=True, context={'request': request}).data

    def get_recipes_count(self, obj):
        """Возвращает общее количество рецептов автора."""
        annotated = getattr(obj, 'recipes_count', None)
        if annotated is not None:
            return annotated
        return obj.recipes.count()


class FollowCreateSerializer(serializers.ModelSerializer):
    """Сериалайзер для создания подписки на автора."""

    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Follow
        fields = ('author',)

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        author = attrs.get('author')

        if user is None or user.is_anonymous:
            raise serializers.ValidationError('Требуется аутентификация.')

        if author == user:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.')

        if Follow.objects.filter(subscriber=user, author=author).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого автора.')

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        author = validated_data['author']
        return Follow.objects.create(subscriber=user, author=author)


class AvatarUploadSerializer(serializers.Serializer):
    """Сериализатор для загрузки/обновления аватара пользователя."""

    avatar = Base64ImageField(required=True)
    MAX_SIZE = MAX_PHOTO_SIZE_BYTES

    class Meta:
        model = User
        fields = ('avatar',)

    def validate_avatar(self, file_obj):
        """Проверяет размер и формат загружаемого изображения (JPG или PNG)."""
        size = getattr(file_obj, 'size', None)
        if size is not None and size > self.MAX_SIZE:
            raise ValidationError('Файл слишком большой (макс. 5 МБ).')

        try:
            data_reader = getattr(file_obj, 'read', None)
            raw = data_reader() if callable(data_reader) else getattr(
                file_obj, 'file', None).read()
        except Exception:
            raw = None

        kind = imghdr.what(None, h=raw) if raw else None
        if kind not in ('jpeg', 'png'):
            raise ValidationError('Допустимы только JPG или PNG.')

        if callable(getattr(file_obj, 'seek', None)):
            file_obj.seek(0)

        return file_obj

    def update(self, instance, validated_data):
        """Обновляет аватар пользователя."""
        instance.avatar = validated_data['avatar']
        instance.save(update_fields=['avatar'])
        return instance
