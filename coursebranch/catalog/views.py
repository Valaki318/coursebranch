import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Q
from .models import Course, Review
from django.contrib.auth.decorators import login_required
from accounts.utils import get_major_requirements

@login_required
def course_detail_view(request, code):
    course = get_object_or_404(Course, code=code)
    filter_type = request.GET.get('filter', 'all')
    search_query = request.GET.get('q', '')
    authenticated = request.user.is_authenticated and hasattr(request.user, 'profile')
    user_courses = None
    if authenticated:
        prof = request.user.profile
        user_courses = prof.completed_courses.all()

    completed_codes = [cs.code for cs in user_courses] if user_courses else []
    
    return render(request, "catalog/course_detail.html", {
        "course": course,
        "prereqs": course.prerequisites.all(),
        "postreqs": Course.objects.filter(prerequisites=course),
        "filter_type": filter_type,
        "search_query": search_query,
        "authenticated": authenticated,
        "completed_codes": completed_codes,
    })

def _get_major_query(major_source, college_name=None):
    """
    Constructs a Q object to filter courses based on a major string.
    Extracts department codes from bu_majors.json and finds ALL courses with those codes in bu_courses.
    """
    if not major_source:
        return Q()
    
    # Get major requirements from bu_majors.json to extract department codes
    major_info = get_major_requirements(major_source, college_name)
    
    if major_info and major_info['required_courses']:
        # Extract department codes from required courses
        dept_codes = set()
        college_codes = set()
        
        for course_code in major_info['required_courses']:
            parts = course_code.strip().split()
            if len(parts) >= 2:
                if len(parts) >= 3:
                    # "CAS CS 101" -> college="CAS", dept="CS"
                    college_codes.add(parts[0])
                    dept_codes.add(parts[1])
                else:
                    # "CS 101" -> dept="CS"
                    dept_codes.add(parts[0])
        
        if dept_codes:
            # Build query to match ALL courses with these department codes
            query = Q()
            for dept in dept_codes:
                # Match courses like "CAS CS 101" or "CS 101"
                # Pattern: (optional college code) + dept code + space + numbers
                dept_query = Q(code__icontains=f' {dept} ') | Q(code__istartswith=f'{dept} ')
                
                # If we know specific colleges, add those patterns too
                if college_codes:
                    for college in college_codes:
                        dept_query |= Q(code__istartswith=f'{college} {dept} ')
                
                query |= dept_query
            
            return query
    
    # Fallback: Manual mapping for common majors
    full_major = major_source.strip().upper()
    
    MAJOR_CODES = {
        "COMPUTER SCIENCE": "CS",
        "COMPUTER SCIENCE/": "CS",  # Added to handle trailing slash
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
        "ECONOMICS": "EC",
        "PSYCHOLOGY": "PS",
    }

    target_code = MAJOR_CODES.get(full_major)
    
    if not target_code and len(full_major) <= 4 and full_major.isalnum():
        target_code = full_major

    if target_code:
        query = Q(code__icontains=f' {target_code} ') | Q(code__istartswith=f'{target_code} ')
        
        if college_name:
            query |= Q(code__istartswith=f'{college_name} {target_code} ')
        
        return query
    else:
        # Name-based search as last resort
        tokens = [t for t in re.split(r'[^a-z0-9]+', major_source.lower()) if t]
        query = Q()
        if tokens:
            name_query = Q()
            for token in tokens:
                name_query &= Q(name__icontains=token)
            query = name_query
        return query

@login_required
def catalog_view(request):
    # Get filter parameter (default to 'all')
    filter_type = request.GET.get('filter', 'all')
    search_query = request.GET.get('q', '').strip()
    
    # Get user's major if logged in
    user_college = None
    user_major = None
    user_courses = None

    authenticated = request.user.is_authenticated and hasattr(request.user, 'profile')
    if authenticated:
        prof = request.user.profile
        user_college = prof.college
        user_major = prof.major
        user_courses = prof.completed_courses.all()
    
    courses_qs = Course.objects.all()

    # Apply Search Filter
    if search_query:
        # Split query into terms
        search_tokens = search_query.split()
        search_q = Q()
        
        # Broad search: Code or Name contains tokens
        # We use AND logic for multi-word search "Data Science" -> Data AND Science
        for token in search_tokens:
            search_q &= (Q(code__icontains=token) | Q(name__icontains=token))
            
        courses_qs = courses_qs.filter(search_q)

    # Apply Major Filter (only if explicitly selected, OR combined?)
    # Usually search overrides categories, but here they can stack.
    # If I select "My Major Only" AND search "Data", I should see Data courses in my major.
    if filter_type == 'major' and user_major:
        # Filter by major using robust logic
        query = _get_major_query(user_major, user_college)
        courses_qs = courses_qs.filter(query)
    elif filter_type == 'major' and not user_major:
        # User wants major filter but has no major set
        courses_qs = Course.objects.none()

    return render(request, "catalog/catalog.html", {
        "courses": courses_qs, # Template expects iterable of objects with .code, .name, etc.
        "filter_type": filter_type,
        "search_query": search_query,
        "user_college": user_college,
        "user_major": user_major,
        "has_major": bool(user_major),
        "authenticated": authenticated,
        "user_courses": user_courses
    })

@login_required
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

def fix_code(code):
    parts = code.strip().upper().split()
    if len(parts) >= 3:
        return f"{parts[1]} {parts[2]}"
    elif len(parts) == 2:
        return f"{parts[0]} {parts[1]}"
    return code.strip().upper()

@login_required
def course_graph_json(request):
    """Returns the JSON data for the Cytoscape graph."""
    major_query = request.GET.get('major')
    profile_major = ''
    profile_college = ''
    completed_course_codes = set()
    required_course_codes = set()
    
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile:
            profile_major = (profile.major or '').strip()
            profile_college = (profile.college or '').strip()
            
            # Get completed courses
            completed_courses = profile.completed_courses.all()
            for course in completed_courses:
                completed_course_codes.add(course.code)
            
            # Get required courses for this major from bu_majors.json
            if profile_major:
                major_info = get_major_requirements(profile_major, profile_college)
                if major_info:
                    # Store normalized versions for matching
                    for req_code in major_info['required_courses']:
                        required_course_codes.add(fix_code(req_code))
            
    major_source = major_query or profile_major
    
    initial_courses = []

    # 1. Initial Query
    if major_source:
        query = _get_major_query(major_source, profile_college)
        initial_courses = list(Course.objects.filter(query))
        print(f"Graph Filter: '{major_source}' -> {len(initial_courses)} initial nodes.")
    
    if not initial_courses:
        # Fallback: If no major or no match, show a small subset (e.g. first 20)
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
        # Check if this course is required (using normalized comparison)
        norm_course_code = fix_code(course.code)
        is_required = norm_course_code in required_course_codes
        is_completed = course.code in completed_course_codes
        
        nodes.append({
            "data": {
                "id": course.code,
                "label": course.code,
                "name": course.name,
                "level": _derive_course_level(course.code),
                "completed": is_completed,
                "required": is_required
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

@login_required
def add_course(request):
    if request.method == "POST" and request.user.is_authenticated:
        course = Course.objects.get(code=request.POST.get("code"))
        prof = request.user.profile
        prof.completed_courses.add(course)
        return JsonResponse({"status": "ok"})

@login_required
def remove_course(request):
    if request.method == "POST" and request.user.is_authenticated:
        course = Course.objects.get(code=request.POST.get("code"))
        prof = request.user.profile
        prof.completed_courses.remove(course)
        return JsonResponse({"status": "ok"})

@login_required
def create_review(request, code):
    course = get_object_or_404(Course, code=code)

    if request.method == "POST":
        Review.objects.create(
            course=course,
            user=request.user,
            rating=request.POST["rating"],
            comment=request.POST["comment"]
        )
        return redirect("course_detail", code=course.code)

    return render(request, "catalog/create_review.html", {"course": course})



