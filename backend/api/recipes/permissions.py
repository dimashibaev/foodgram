from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthorOrAdminOrReadOnly(BasePermission):
    """
    Права доступа к объекту.

    GET/HEAD/OPTIONS — доступны всем.
    POST/PATCH/PUT/DELETE — только автору объекта или суперпользователю.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        author_id = getattr(obj, 'author_id', None)
        is_author = user.is_authenticated and author_id == user.id
        return is_author or (user and user.is_superuser)
