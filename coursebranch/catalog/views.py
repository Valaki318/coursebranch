import json
import os
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
        
    courses = []
    for c in courses_data:
        courses.append({
            'code': c.get('course_code'),
            'name': c.get('course_name'),
            'description': c.get('description'),
            'credits': 4,
            'instructor': 'TBA' 
        })
        
    return render(request, "catalog/catalog.html", {"courses": courses})

def course_tree_view(request):
    """Renders the static HTML page for the Cytoscape graph."""
    return render(request, "catalog/tree_cytoscape.html")

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
                "name": course['course_name']
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
