
from Scraper import scrape_prerequisites

import _json
import requests
from bs4 import BeautifulSoup
import re

"""BOSTON UNIVERSITY COURSE CATALOG PARSER"""

url = "https://www.bu.edu/academics/bulletin/"

response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

# Select all <a> tags that look like course links
course_links = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    # Filter for links containing '/courses/' and ensure they are full URLs
    if "/courses" in href:
        if href.startswith("http"):
            course_links.append(href)
        else:
            # Make relative links absolute
            course_links.append(requests.compat.urljoin(url, href))


# For each course link, find the max associated paginated page and collect the URL
max_paginated_urls = []
for link in course_links:
    try:
        resp = requests.get(link)
        page_soup = BeautifulSoup(resp.text, "html.parser")
        title = page_soup.title.string.strip() if page_soup.title else "No Title"
        print(f"Visited: {link} | Title: {title}")

        dept_match = re.search(r"/academics/([a-z]+)/courses", link)
        dept = dept_match.group(1) if dept_match else None
        pattern = re.compile(rf"/academics/{dept}/courses/(\d+)") if dept else None
        numbers = []
        if pattern:
            for a in page_soup.find_all("a", href=True):
                match = pattern.search(a["href"])
                if match:
                    numbers.append(int(match.group(1)))
            if numbers:
                max_value = max(numbers)
                max_paginated_urls.append(f"https://www.bu.edu/academics/{dept}/courses/{max_value}")
            else:
                max_paginated_urls.append(f"https://www.bu.edu/academics/{dept}/courses/0")
        else:
            print(f"Not a department course link: {link}")
    except Exception as e:
        print(f"Failed to visit {link}: {e}")

print("\nAll max paginated course URLs:")
for url in max_paginated_urls:
    print(url)

# Function to process a single page using parserHelper logic
def process_course_page(page_url):
    try:
        response = requests.get(page_url)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all elements with class="course-feed"
        course_feed_elements = soup.find_all(class_="course-feed")
        courses = []
        
        for course_feed in course_feed_elements:
            # Find all <li> elements within this course-feed
            li_elements = course_feed.find_all('li')
            
            for li in li_elements:
                # Get all text content from this <li>
                full_text = li.get_text(strip=True)
                
                # Try to find title (usually the first line or in a strong/bold element)
                title = ""
                strong_tag = li.find('strong')
                if strong_tag:
                    title = strong_tag.get_text(strip=True)
                else:
                    # If no strong tag, use first line as title
                    lines = full_text.split('\n')
                    title = lines[0].strip() if lines else ""
                
                # Description is the remaining text after title
                description = full_text

                # Parse title to separate course code and name
                course_code = ""
                course_name = ""
                if title and ':' in title:
                    parts = title.split(':', 1)
                    course_code = parts[0].strip()
                    course_name = parts[1].strip()
                else:
                    course_code = title if title else ""
                
                # Extract required courses using Scraper
                try:
                    required_courses = scrape_prerequisites(description)
                except Exception:
                    required_courses = []
                
                # Create course object for each <li>
                course_obj = {
                    'course_code': course_code,
                    'course_name': course_name,
                    'description': description,
                    'required_courses': required_courses
                }
                courses.append(course_obj)
        return courses
    except Exception as e:
        print(f"Failed to process {page_url}: {e}")
        return []

# Function to create course objects from max_paginated_urls
def create_college_course(max_paginated_urls):
    all_courses = []
    for max_url in max_paginated_urls:
        # Extract base and max_value
        match = re.match(r"(https://www\.bu\.edu/academics/[a-z]+/courses/)(\d+)", max_url)
        if not match:
            continue
        base_url, max_value = match.groups()
        max_value = int(max_value)
        
        # Visit each page from max down to 0
        for n in range(max_value, -20, -20):
            page_url = f"{base_url}{n}/"
            courses = process_course_page(page_url)
            all_courses.extend(courses)
    
    return all_courses

# Create all course objects and filter out those without course names
courses = create_college_course(max_paginated_urls)
print(f"Total courses collected: {len(courses)}")

# Filter out courses without course names
filtered_courses = [course for course in courses if course.get('course_name', '').strip()]
print(f"Courses with names: {len(filtered_courses)}")

# Export to JSON file
import json
with open('bu_courses.json', 'w', encoding='utf-8') as f:
    json.dump(filtered_courses, f, indent=2, ensure_ascii=False)

print("Course data exported to bu_courses.json")

# Example: show first course object
if filtered_courses:
    print("First course object:")
    print(filtered_courses[0])
else:
    print("No course objects found.")












