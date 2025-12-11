from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from catalog.models import Course
from django.db.models import Avg, Q

def explain_recommendation(course, user):
    avg_rating = course.average_rating()
    rating_phrase = (
        "highly rated by other students"
        if avg_rating >= 4
        else "well-rated overall"
        if avg_rating >= 3
        else "mixed reviews"
    )

    major_match = (
        f"fits well with your major ({user.profile.major})"
        if user.profile.major.lower() in course.description.lower()
           or user.profile.major.lower() in course.name.lower()
        else "could complement your major"
    )

    return (
        f"{rating_phrase}, {major_match}. "
    )

def recommend_courses_for_user(user):
    profile = user.profile
    completed_ids = profile.completed_courses.values_list("id", flat=True)

    qs = Course.objects.exclude(id__in=completed_ids)

    eligible = []
    for c in qs:
        prereq_ids = c.prerequisites.values_list("id", flat=True)
        if all(pid in completed_ids for pid in prereq_ids):
            eligible.append(c)

    recommended = []

    for course in eligible:
        score = 0
        score += course.average_rating()

        if profile.major:
            major = profile.major.lower()
            if major in course.name.lower() or major in course.description.lower():
                score += 3  
            elif major.split()[0] in course.description.lower():
                score += 1 

        if profile.college and profile.college == course.college.name:
            score += 1.5

        recommended.append({
            "course": course,
            "score": score,
            "reason": explain_recommendation(course, user),
        })

    recommended.sort(key=lambda x: x["score"], reverse=True)

    return recommended

@login_required
def recommendations(request):
    recs = recommend_courses_for_user(request.user)
    return render(request, "recommendations/recommendations.html", {
        "recs": recs
    })