import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from catalog.models import Course, College, University

class Command(BaseCommand):
    help = 'Imports courses from bu_courses.json'

    def handle(self, *args, **kwargs):
        json_path = os.path.join(settings.BASE_DIR, 'bu_courses.json')
        
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'File not found: {json_path}'))
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # ensure university
        uni, _ = University.objects.get_or_create(name="Boston University", defaults={"location": "Boston, MA"})
        
        # Pass 1: Create Courses
        self.stdout.write(f"Processing {len(data)} courses...")
        
        courses_created = 0
        courses_updated = 0
        
        # Cache colleges to avoid DB hits
        colleges = {} # name -> College obj
        
        for item in data:
            code = item.get('course_code', '').strip()
            if not code:
                continue
                
            # Infer college from code (e.g. "CAS CS 101" -> "CAS")
            parts = code.split()
            college_name = parts[0] if parts else "Unknown"
            
            if college_name not in colleges:
                col, _ = College.objects.get_or_create(name=college_name, university=uni)
                colleges[college_name] = col
            
            course_obj, created = Course.objects.update_or_create(
                code=code,
                defaults={
                    'name': item.get('course_name', 'Unknown'),
                    'description': item.get('description', ''),
                    'college': colleges[college_name],
                    'credits': 4, # Default
                    'instructor': 'TBA'
                }
            )
            if created:
                courses_created += 1
            else:
                courses_updated += 1
                
        self.stdout.write(self.style.SUCCESS(f'Pass 1 Complete: {courses_created} created, {courses_updated} updated.'))

        # Pass 2: Link Prerequisites
        self.stdout.write("Pass 2: Linking prerequisites...")
        links_created = 0
        
        all_courses = list(Course.objects.all())
        course_map = {c.code: c for c in all_courses}
        
        # Suffix map for fuzzy matching
        suffix_map = {}
        for c in all_courses:
            # Suffix could be "CS 101"
            parts = c.code.split()
            if len(parts) >= 2:
                suffix = " ".join(parts[1:]) # "CS 101"
                if suffix not in suffix_map:
                    suffix_map[suffix] = []
                suffix_map[suffix].append(c)
        
        for item in data:
            code = item.get('course_code', '').strip()
            reqs = item.get('required_courses', [])
            
            if not code or not reqs:
                continue
                
            current_course = course_map.get(code)
            if not current_course:
                continue
            
            # Clear existing to avoid stale
            current_course.prerequisites.clear()
            
            for req in reqs:
                # req is e.g. "CS 101"
                prereq_obj = course_map.get(req)
                
                if not prereq_obj:
                    # Try suffix match
                    candidates = suffix_map.get(req)
                    if candidates:
                        best_candidate = candidates[0]
                        for cand in candidates:
                            if cand.college.name == 'CAS':
                                best_candidate = cand
                                break
                        prereq_obj = best_candidate
                
                if prereq_obj:
                    current_course.prerequisites.add(prereq_obj)
                    links_created += 1
                    
        self.stdout.write(self.style.SUCCESS(f'Pass 2 Complete: {links_created} prerequisite links created.'))

