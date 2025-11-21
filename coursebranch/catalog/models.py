from django.db import models

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
