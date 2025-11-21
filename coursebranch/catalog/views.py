import json
import os
import re
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from .models import Course

def course_detail_view(request, code):
    course = get_object_or_404(Course, code=code)
    return render(request, "catalog/course_detail.html", {
        "course": course,
        "prereqs": course.prerequisites.all(),
        "postreqs": Course.objects.filter(prerequisites=course)
    })

def catalog_view(request):
    json_path = os.path.join(settings.BASE_DIR, 'bu_courses.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        courses_data = json.load(f)
    
    # Get filter parameter (default to 'all')
    filter_type = request.GET.get('filter', 'all')
    
    # Get user's major if logged in
    user_college = None
    user_major = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_college = request.user.profile.college
        user_major = request.user.profile.major
    
    courses = []
    for c in courses_data:
        course_code = c.get('course_code', '')
        
        # Apply filtering
        if filter_type == 'major' and user_college and user_major:
            # Expected format: "COLLEGE DEPT NUMBER" (e.g., "CAS CS 101")
            parts = course_code.split()
            if len(parts) >= 2:
                course_college = parts[0]
                course_dept = parts[1]
                # Only show courses matching user's college and major
                if not (course_college == user_college and course_dept == user_major):
                    continue
            else:
                continue  # Skip courses with invalid format
        
        courses.append({
            'code': course_code,
            'name': c.get('course_name'),
            'description': c.get('description'),
            'credits': 4,
            'instructor': 'TBA' 
        })
    
    return render(request, "catalog/catalog.html", {
        "courses": courses,
        "filter_type": filter_type,
        "user_college": user_college,
        "user_major": user_major,
        "has_major": bool(user_college and user_major)
    })

def course_tree_view(request):
    """Renders the static HTML page for the Cytoscape graph."""
    return render(request, "catalog/tree_cytoscape.html")

def _derive_course_level(code: str) -> str:
    """Return the nearest hundred level as a string (e.g., '100', '200')."""
    if not code:
        return "OTHER"
    digits = re.findall(r"\d+", code)
    if not digits:
        return "OTHER"
    number = int(digits[0])
    if number < 100:
        return "OTHER"
    bucket = min(500, (number // 100) * 100)
    return str(bucket)


def course_graph_json(request):
    """Returns the JSON data for the Cytoscape graph."""
    
    # Always use small dataset for now as requested
    json_filename = 'bu_courses_small.json'
    
    json_path = os.path.join(settings.BASE_DIR, json_filename)
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    nodes = []
    edges = []
    course_codes = set(c['course_code'] for c in data)

    for course in data:
        code = course['course_code']
        
        # Add Node
        nodes.append({
            "data": {
                "id": code,
                "label": code,
                "name": course['course_name'],
                "level": _derive_course_level(code)
            }
        })

        # Add Edges
        for req in course.get('required_courses', []):
            target = code
            source = req
            
            # Normalize logic
            if source not in course_codes:
                match = None
                for real_code in course_codes:
                    if real_code.endswith(source):
                        match = real_code
                        break
                if match:
                    source = match
            
            if source in course_codes:
                edges.append({
                    "data": {
                        "source": source,
                        "target": target
                    }
                })

    return JsonResponse({"elements": {"nodes": nodes, "edges": edges}})
