from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import Profile
from .forms import SignUpForm
from catalog.models import Course
import json
import os


def get_colleges_and_majors():
    """Parses bu_courses.json to extract unique colleges and their majors (departments)."""
    json_path = os.path.join(settings.BASE_DIR, 'bu_courses.json')
    data = {}
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            courses = json.load(f)
            for course in courses:
                code = course.get('course_code', '')
                # Expected format: "COLLEGE DEPT NUMBER" e.g. "CAS CS 101"
                parts = code.split()
                if len(parts) >= 2:
                    college = parts[0]
                    dept = parts[1]
                    if college not in data:
                        data[college] = set()
                    data[college].add(dept)
    except FileNotFoundError:
        pass
    
    # Convert sets to sorted lists
    sorted_data = {}
    for college, depts in data.items():
        sorted_data[college] = sorted(list(depts))
    
    return sorted_data


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, f"Welcome to CourseBranch, {user.username}!")
            return redirect('onboarding')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def home_view(request):
    """Simple home page with or without login"""
    return render(request, 'home.html')


@login_required
def profile_view(request):
    """Basic profile editing (college/major/year/bio)"""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    # Get structure: { 'CAS': ['CS', 'MA', ...], 'ENG': [...] }
    colleges_data = get_colleges_and_majors()
    college_list = sorted(colleges_data.keys())

    if request.method == 'POST':
        profile.bio = request.POST.get('bio', '')
        profile.college = request.POST.get('college', '')
        profile.major = request.POST.get('major', '')
        year = request.POST.get('graduation_year')
        profile.graduation_year = int(year) if year else None

        profile.save()
        messages.success(request, "Profile updated!")
        return redirect('profile')

    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'colleges_data': json.dumps(colleges_data), # Pass as JSON for JS
        'college_list': college_list
    })

@login_required
def courses_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    filter_type = request.GET.get('filter', 'all')
    search_query = request.GET.get('q', '').strip()
    courses_qs = []
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        prof = request.user.profile
        courses_qs = prof.completed_courses.all()

    return render(request, "accounts/completed_courses.html", {
        "courses": courses_qs, 
        "filter_type": filter_type,
        "search_query": search_query,
    })

@login_required
def add_completed_courses_view(request):
    from django.db.models import Q
    
    profile, _ = Profile.objects.get_or_create(user=request.user)
    filter_type = request.GET.get('filter', 'all')
    search_query = request.GET.get('q', '').strip()
    
    completed_courses = profile.completed_courses.all()
    completed_codes = set(c.code for c in completed_courses)
    
    available_courses = Course.objects.exclude(code__in=completed_codes)
    
    if search_query:
        search_tokens = search_query.split()
        search_q = Q()
        for token in search_tokens:
            search_q &= (Q(code__icontains=token) | Q(name__icontains=token))
        available_courses = available_courses.filter(search_q)
    
    if filter_type == 'major' and profile.major:
        from catalog.views import _get_major_query
        query = _get_major_query(profile.major)
        if profile.college:
            query &= Q(college__name__icontains=profile.college)
        available_courses = available_courses.filter(query)
    elif filter_type == 'major' and not profile.major:
        available_courses = Course.objects.none()
    
    limit = 100
    available_courses = available_courses[:limit]

    return render(request, "accounts/add_completed_courses.html", {
        "completed_courses": completed_courses,
        "available_courses": available_courses,
        "filter_type": filter_type,
        "search_query": search_query,
        "user_college": profile.college,
        "user_major": profile.major,
        "has_major": bool(profile.major),
    })

@login_required
def change_username_view(request):
    if request.method == 'POST':
        new_username = request.POST.get('username', '').strip()
        
        if not new_username:
            messages.error(request, "Username cannot be empty.")
            return redirect('change_username')
        
        if request.user.username == new_username:
            messages.info(request, "This is already your username.")
            return redirect('profile')
        
        from django.contrib.auth.models import User
        if User.objects.filter(username=new_username).exists():
            messages.error(request, "Username already taken. Please choose another.")
            return redirect('change_username')
        
        request.user.username = new_username
        request.user.save()
        messages.success(request, "Username updated successfully!")
        return redirect('profile')
    
    return render(request, 'accounts/change_username.html')

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully!")
            return redirect('profile')
        else:
            for error in form.errors.values():
                messages.error(request, error.as_text())
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
def onboarding_view(request):
    from django.db.models import Q
    
    profile, _ = Profile.objects.get_or_create(user=request.user)
    colleges_data = get_colleges_and_majors()
    college_list = sorted(colleges_data.keys())
    
    if request.method == 'POST':
        profile.college = request.POST.get('college', '')
        profile.major = request.POST.get('major', '')
        year = request.POST.get('graduation_year')
        profile.graduation_year = int(year) if year else None
        profile.save()
        
        messages.success(request, "Profile saved! You can now add completed courses below, or continue to CourseBranch.")
        return redirect('onboarding')
    
    filter_type = request.GET.get('filter', 'all')
    search_query = request.GET.get('q', '').strip()
    
    completed_courses = profile.completed_courses.all()
    completed_codes = set(c.code for c in completed_courses)
    
    available_courses = Course.objects.exclude(code__in=completed_codes)
    
    if search_query:
        search_tokens = search_query.split()
        search_q = Q()
        for token in search_tokens:
            search_q &= (Q(code__icontains=token) | Q(name__icontains=token))
        available_courses = available_courses.filter(search_q)
    
    if filter_type == 'major' and profile.major:
        from catalog.views import _get_major_query
        query = _get_major_query(profile.major)
        if profile.college:
            query &= Q(college__name__icontains=profile.college)
        available_courses = available_courses.filter(query)
    elif filter_type == 'major' and not profile.major:
        available_courses = Course.objects.none()
    
    limit = 100
    available_courses = available_courses[:limit]

    return render(request, "accounts/onboarding.html", {
        "profile": profile,
        "colleges_data": json.dumps(colleges_data),
        "college_list": college_list,
        "completed_courses": completed_courses,
        "available_courses": available_courses,
        "filter_type": filter_type,
        "search_query": search_query,
        "user_college": profile.college,
        "user_major": profile.major,
        "has_major": bool(profile.major),
    })

