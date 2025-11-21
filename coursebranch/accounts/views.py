from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import Profile
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
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
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
