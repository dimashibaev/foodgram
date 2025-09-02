from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Follow, User


@admin.register(User)
class MyUserAdmin(UserAdmin):
    list_display = (
        'id', 'email', 'username', 'first_name',
        'last_name', 'is_staff', 'is_active',
    )
    list_display_links = ('email', 'username')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'username')}),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions',
            )
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'first_name',
                'last_name', 'password1', 'password2',
            ),
        }),
    )


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('subscriber', 'author', 'id')
    list_display_links = ('subscriber', 'author')
    list_filter = ('subscriber', 'author')
    search_fields = ('subscriber__email', 'author__email')
    ordering = ('id',)
    list_select_related = ('subscriber', 'author')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('subscriber', 'author')
