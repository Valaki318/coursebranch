from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg

class University(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class College(models.Model):
    university = models.ForeignKey(
        University, on_delete=models.CASCADE, related_name='colleges'
    )
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name} ({self.university.name})"


class Course(models.Model):
    college = models.ForeignKey(
        College, on_delete=models.CASCADE, related_name="courses"
    )
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    instructor = models.CharField(max_length=100)
    credits = models.IntegerField()

    prerequisites = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='required_for'
    )

    def __str__(self):
        return f"{self.code}: {self.name}"

    def average_rating(self):
        return self.reviews.aggregate(avg=Avg("rating"))["avg"] or 0

class Review(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # optional but recommended
    rating = models.IntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.course.code} by {self.user.username}"
