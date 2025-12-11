from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from catalog.models import Course
from django.db.models import Avg, Q, Count
from catalog.views import _get_major_query
from accounts.utils import get_major_requirements

def fix_code(code):
        parts = code.strip().upper().split()
        if len(parts) >= 3:
            return f"{parts[1]} {parts[2]}"
        elif len(parts) == 2:
            return f"{parts[0]} {parts[1]}"
        return code.strip().upper()

def recomm_text(course, user, is_required=False):
    avg_rating = course.average_rating()
    reasons = ""
    rating_phrase = (
        "Highly rated. "
        if avg_rating >= 4
        else "Well-rated. "
        if avg_rating >= 3
        else "Poorly rated. "
        if avg_rating > 0
        else "not yet rated"
    )
    
    if is_required:
        reasons += f"Required for your major. "
    
    if avg_rating > 0:
        reasons+= rating_phrase
    
    if user.profile.major:
        major_query = _get_major_query(user.profile.major, user.profile.college)
        if Course.objects.filter(id=course.id).filter(major_query).exists():
            if not is_required:
                reasons += f"Part of your major curriculum. "
    
    if user.profile.college and user.profile.college in course.code:
        reasons += f"Offered by your college. "
    
    if not reasons:
        reasons += "Available based on your completed prerequisites."
    
    return reasons

def recommend_courses_for_user(user):
    profile = user.profile
    completed_courses = profile.completed_courses.all()
    completed_ids = list(completed_courses.values_list("id", flat=True))
    normalized_completed = {fix_code(code) for code in set(c.code for c in completed_courses)}
    required_course_codes = set()
    major_courses_query = Q()
    
    if profile.major:
        major_info = get_major_requirements(profile.major, profile.college)
        if major_info:
            required_course_codes = {fix_code(code) for code in major_info['required_courses']}
        major_courses_query = _get_major_query(profile.major, profile.college)
    
    pcourses = Course.objects.exclude(id__in=completed_ids)
    if profile.major:
        pcourses = pcourses.filter(
            major_courses_query | Q(reviews__rating__gte=4)
        ).distinct()
    
    
    pcourses = pcourses[:200]
    eligible = []
    
    for c in pcourses:
        prereq_codes = list(c.prerequisites.values_list("code", flat=True))
        all_prereqs_met = True
        for prereq_code in prereq_codes:
            norm_prereq = fix_code(prereq_code)
            if norm_prereq not in normalized_completed:
                all_prereqs_met = False
                break
        
        if all_prereqs_met:
            eligible.append(c)
    
    recommended = []

    for course in eligible:
        score = 0
        course_code = fix_code(course.code)
        if course_code in required_course_codes:
            score += 10
        score += course.average_rating() * 2  

        if profile.major and major_courses_query:
            if Course.objects.filter(id=course.id).filter(major_courses_query).exists():
                score += 5

        if profile.college and profile.college in course.code:
            score += 2
        recommended.append({
            "course": course,
            "score": score,
            "reason": recomm_text(course, user, course_code in required_course_codes),
            "is_required": course_code in required_course_codes,
        })

    recommended.sort(key=lambda x: x["score"], reverse=True)
    return recommended[:50]

@login_required
def recommendations(request):
    recs = recommend_courses_for_user(request.user)
    return render(request, "recommendations/recommendations.html", {
        "recs": recs
    })