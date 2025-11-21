from django.db import models
from django.contrib.auth.models import User
class Profile(models.Model):
    """Extended user information."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, max_length=500)
    major = models.CharField(max_length=100, blank=True)
    graduation_year = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
