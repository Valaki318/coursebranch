from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'major', 'graduation_year')
    search_fields = ('user__username', 'major')
