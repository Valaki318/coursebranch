import json
import os
import re
from django.conf import settings
from difflib import SequenceMatcher


def get_colleges_and_majors():
    """
    Parses bu_majors.json to extract colleges and their majors.
    Returns dict: { 'CAS': ['Computer Science', 'Mathematics', ...], 'ENG': [...], ... }
    """
    json_path = os.path.join(settings.BASE_DIR, 'bu_majors.json')
    
    if not os.path.exists(json_path):
        return {}
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            majors_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}
    
    college_majors = {}
    college_codes = ['CAS', 'COM', 'ENG', 'CFA', 'QST', 'CDS', 'SAR', 'SHA', 'STH', 'GRS', 'SPH', 'SSW', 'Wheelock']
    
    for major in majors_data:
        major_name = major.get('name', '').strip()
        if not major_name:
            continue
        
        # Extract college code from major name
        # Format: "Computer ScienceCAS(BA,minor)" or "Acting" (CFA)
        college_found = None
        
        for college_code in college_codes:
            if college_code in major_name:
                college_found = college_code
                break
        
        # If no college code found in name, check the required courses
        if not college_found:
            required_courses = major.get('required_courses', [])
            if required_courses and len(required_courses) > 0:
                # Get college from first course code (e.g., "CFA TH 100" -> "CFA")
                first_course = required_courses[0]
                parts = first_course.split()
                if parts:
                    potential_college = parts[0]
                    if potential_college in college_codes:
                        college_found = potential_college
        
        # Default to "Other" if no college found
        if not college_found:
            college_found = "Other"
        
        # Clean up major name (remove college code and degree info)
        clean_name = major_name
        for college_code in college_codes:
            clean_name = clean_name.replace(college_code, '')
        
        # Remove parentheses content (degree types)
        if '(' in clean_name:
            clean_name = clean_name.split('(')[0]
        
        clean_name = clean_name.strip()
        
        if college_found not in college_majors:
            college_majors[college_found] = []
        
        # Avoid duplicates
        if clean_name and clean_name not in college_majors[college_found]:
            college_majors[college_found].append(clean_name)
    
    # Sort majors alphabetically within each college
    for college in college_majors:
        college_majors[college].sort()
    
    return college_majors


def get_major_requirements(major_name, college_name=None):
    """
    Parses bu_majors.json to find required courses for a given major.
    Returns dict with: {
        'major_name': str,
        'degree': str,
        'required_courses': list[str],
        'total_required': int,
        'match_score': float (0-1)
    }
    Returns None if no match found.
    """
    if not major_name:
        return None
    
    json_path = os.path.join(settings.BASE_DIR, 'bu_majors.json')
    
    if not os.path.exists(json_path):
        return None
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            majors_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
    
    # Normalize user's major for comparison
    user_major_lower = major_name.lower().strip()
    
    # Try exact match first (case-insensitive)
    for major in majors_data:
        major_full_name = major.get('name', '')
        if major_full_name.lower() == user_major_lower:
            return {
                'major_name': major_full_name,
                'degree': major.get('degree', ''),
                'required_courses': major.get('required_courses', []),
                'total_required': len(major.get('required_courses', [])),
                'match_score': 1.0
            }
    
    # Try fuzzy matching
    best_match = None
    best_score = 0.0
    
    for major in majors_data:
        major_full_name = major.get('name', '')
        
        # Extract base major name (before parentheses or college codes)
        # e.g., "Computer ScienceCAS(BA,minor)" -> "Computer Science"
        base_name = major_full_name
        
        # Remove college codes (CAS, COM, ENG, etc.) at the end
        for college_code in ['CAS', 'COM', 'ENG', 'CFA', 'QST', 'CDS', 'SAR', 'SHA', 'STH', 'GRS', 'SPH', 'SSW']:
            if college_code in base_name:
                base_name = base_name.split(college_code)[0]
                break
        
        # Remove parentheses and everything after
        if '(' in base_name:
            base_name = base_name.split('(')[0]
        
        base_name = base_name.strip()
        
        # Calculate similarity score
        score = SequenceMatcher(None, user_major_lower, base_name.lower()).ratio()
        
        # Boost score if user's major is contained in the base name
        if user_major_lower in base_name.lower():
            score += 0.2
        
        # Boost score if college matches (if provided)
        if college_name and college_name.upper() in major_full_name.upper():
            score += 0.1
        
        score = min(score, 1.0)
        
        if score > best_score:
            best_score = score
            best_match = major
    
    # Only return if we have a reasonable match (>= 60% similarity)
    if best_match and best_score >= 0.6:
        return {
            'major_name': best_match.get('name', ''),
            'degree': best_match.get('degree', ''),
            'required_courses': best_match.get('required_courses', []),
            'total_required': len(best_match.get('required_courses', [])),
            'match_score': best_score
        }
    
    return None


def calculate_degree_progress(profile):
    """
    Calculates degree progress for a user profile.
    Returns dict with: {
        'required_courses': list[str],
        'completed_required': list[str],
        'total_required': int,
        'completed_count': int,
        'percentage': float,
        'major_info': dict or None
    }
    """
    major_info = get_major_requirements(profile.major, profile.college)
    
    if not major_info:
        return {
            'required_courses': [],
            'completed_required': [],
            'total_required': 0,
            'completed_count': 0,
            'percentage': 0.0,
            'major_info': None
        }
    
    required_codes = set(major_info['required_courses'])
    completed_courses = profile.completed_courses.all()
    completed_codes = set(c.code for c in completed_courses)
    
    # Find which required courses have been completed
    completed_required = required_codes.intersection(completed_codes)
    
    total = len(required_codes)
    completed = len(completed_required)
    percentage = (completed / total * 100) if total > 0 else 0.0
    
    return {
        'required_courses': sorted(list(required_codes)),
        'completed_required': sorted(list(completed_required)),
        'total_required': total,
        'completed_count': completed,
        'percentage': round(percentage, 1),
        'major_info': major_info
    }

