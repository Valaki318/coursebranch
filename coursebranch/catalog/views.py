import re
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from .models import Course

def course_detail_view(request, code):
    course = get_object_or_404(Course, code=code)
    filter_type = request.GET.get('filter', 'all')
    return render(request, "catalog/course_detail.html", {
        "course": course,
        "prereqs": course.prerequisites.all(),
        "postreqs": Course.objects.filter(prerequisites=course),
        "filter_type": filter_type
    })

def _get_major_query(major_source):
    """
    Constructs a Q object to filter courses based on a major string.
    Uses mapping for known majors and strict code matching.
    """
    if not major_source:
        return Q()

    full_major = major_source.strip().upper()
    
    # Common Major to Dept Code Mapping
    MAJOR_CODES = {
        "COMPUTER SCIENCE": "CS",
        "COMP SCI": "CS",
        "CS": "CS",
        "COMPUTER ENGINEERING": "EC",
        "ELECTRICAL ENGINEERING": "EC",
        "MECHANICAL ENGINEERING": "ME",
        "BIOMEDICAL ENGINEERING": "BE",
        "MATHEMATICS": "MA",
        "PHYSICS": "PY",
        "CHEMISTRY": "CH",
        "BIOLOGY": "BI",
        "ECONOMICS": "EC", # Note: BU Economics is CAS EC. ENG EC is ECE. Overlap risk? 
                           # CAS EC vs ENG EC. We filter by code.
                           # "CAS EC" vs "ENG EC".
        "PSYCHOLOGY": "PS",
    }

    target_code = MAJOR_CODES.get(full_major)
    
    # Heuristic: If major is short (<=4 chars), assume it's a code (e.g. "CS", "ENG")
    if not target_code and len(full_major) <= 4 and full_major.isalnum():
        target_code = full_major

    if target_code:
        # Strict Code Matching
        # Matches "CAS CS 101" (contains " CS ")
        # Matches "CS 101" (starts with "CS ")
        # Avoids "PHYSICS" matching "CS" (no " CS " in "CAS PY...")
        query = Q(code__icontains=f" {target_code} ") | Q(code__startswith=f"{target_code} ")
        
        # Also allow standard college prefixes explicitly for safety
        query |= Q(code__istartswith=f"CAS {target_code} ")
        query |= Q(code__istartswith=f"ENG {target_code} ")
        query |= Q(code__istartswith=f"QST {target_code} ")
        query |= Q(code__istartswith=f"COM {target_code} ")
        
    else:
        # Fallback: Name must contain ALL tokens (AND logic)
        # e.g. "Political Science" -> Name contains "Political" AND "Science"
        tokens = [t for t in re.split(r'[^a-z0-9]+', major_source.lower()) if t]
        query = Q()
        if tokens:
            name_query = Q()
            for token in tokens:
                name_query &= Q(name__icontains=token)
            query = name_query
    
    return query

def catalog_view(request):
    # Get filter parameter (default to 'all')
    filter_type = request.GET.get('filter', 'all')
    
    # Get user's major if logged in
    user_college = None
    user_major = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_college = request.user.profile.college
        user_major = request.user.profile.major
    
    courses_qs = Course.objects.all()

    if filter_type == 'major' and user_major:
        # Filter by major using robust logic
        query = _get_major_query(user_major)
        if user_college:
             # Also filter by college if available
             query &= Q(college__name__icontains=user_college)
        courses_qs = courses_qs.filter(query)
    elif filter_type == 'major' and not user_major:
        # User wants major filter but has no major set
        courses_qs = Course.objects.none()

    return render(request, "catalog/catalog.html", {
        "courses": courses_qs, # Template expects iterable of objects with .code, .name, etc.
        "filter_type": filter_type,
        "user_college": user_college,
        "user_major": user_major,
        "has_major": bool(user_major)
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
    major_query = request.GET.get('major')
    profile_major = ''
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile:
            profile_major = (profile.major or '').strip()
            
    major_source = major_query or profile_major
    
    initial_courses = []

    # 1. Initial Query
    if major_source:
        query = _get_major_query(major_source)
        initial_courses = list(Course.objects.filter(query))
        print(f"Graph Filter: '{major_source}' -> {len(initial_courses)} initial nodes.")
    
    if not initial_courses:
        # Fallback: If no major or no match, show a small subset (e.g. first 20)
        # per user request to limit size.
        print("Graph Filter: Fallback to first 20 courses.")
        initial_courses = list(Course.objects.all()[:20])

    if not initial_courses:
         return JsonResponse({"elements": {"nodes": [], "edges": []}})

    # 2. Traverse Prereqs to ensure connectivity
    final_courses = set(initial_courses)
    queue = list(final_courses)
    visited_ids = {c.id for c in final_courses}
    
    while queue:
        current = queue.pop(0)
        # Efficiently fetch prereqs
        prereqs = current.prerequisites.all()
        for p in prereqs:
            if p.id not in visited_ids:
                visited_ids.add(p.id)
                final_courses.add(p)
                queue.append(p)

    # 3. Build Graph
    nodes = []
    edges = []
    
    # Sort by code for consistent order
    sorted_courses = sorted(list(final_courses), key=lambda x: x.code)

    for course in sorted_courses:
        nodes.append({
            "data": {
                "id": course.code,
                "label": course.code,
                "name": course.name,
                "level": _derive_course_level(course.code)
            }
        })
        
        for p in course.prerequisites.all():
            # Only add edge if source is also in the graph
            if p in final_courses:
                edges.append({
                    "data": {
                        "source": p.code,
                        "target": course.code
                    }
                })
                
    return JsonResponse({"elements": {"nodes": nodes, "edges": edges}})
