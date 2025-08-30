from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthorOrAdminOrReadOnly(BasePermission):
    '''
    GET/HEAD/OPTIONS — всем.
    POST/PATCH/PUT/DELETE — только автору объекта или администратору.
    '''

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        u = request.user
        return (
            getattr(obj, 'author_id', None) == getattr(u, 'id', None)
            or (u and u.is_superuser)
        )
