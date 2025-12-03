from django.contrib import admin
from .models import Course, College, University

# Register your models here.
admin.site.register(Course)
admin.site.register(College)
admin.site.register(University)
