
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
            # Find all <a> links within this course-feed
            links = course_feed.find_all('a', href=True)
            
            for link in links:
                # Skip links that are inside "cf-hub-ind" div class
                if link.find_parent(class_="cf-hub-ind"):
                    continue
                    
                href = link['href']
                print(f"Found link: {href}")
                
                # Fetch the linked page to get course description
                try:
                    course_response = requests.get(f"https://www.bu.edu{href}")
                    if course_response.status_code == 200:
                        course_soup = BeautifulSoup(course_response.text, 'html.parser')
                        course_content_div = course_soup.find('div', id='course-content')
                        if course_content_div:
                            p_tag = course_content_div.find('p')
                            description = p_tag.get_text(strip=True) if p_tag else ""
                        else:
                            description = ""
                        
                        # Extract credits from info-box
                        credits = ""
                        info_box = course_soup.find('div', id='info-box', class_='sidebar')
                        if info_box:
                            dt_tags = info_box.find_all('dt')
                            dd_tags = info_box.find_all('dd')
                            for dt, dd in zip(dt_tags, dd_tags):
                                if 'Units:' in dt.get_text(strip=True):
                                    credits = dd.get_text(strip=True)
                                    break
                        
                        # Extract hub credits
                        hub_credit = []
                        hub_offerings = course_soup.find('ul', class_='cf-hub-offerings')
                        if hub_offerings:
                            li_tags = hub_offerings.find_all('li')
                            for li in li_tags:
                                hub_credit.append(li.get_text(strip=True))
                        
                        # Extract instructors
                        instructors = []
                        # Check all tables in cf-course elements
                        cf_courses = course_soup.find_all('cf-course')
                        for cf_course in cf_courses:
                            tables = cf_course.find_all('table')
                            for table in tables:
                                rows = table.find_all('tr')
                                for row in rows:
                                    cells = row.find_all('td')
                                    if len(cells) >= 2:
                                        instructor = cells[1].get_text(strip=True)
                                        if instructor and instructor not in instructors:
                                            instructors.append(instructor)
                        
                        # Also check any tables outside cf-course elements
                        all_tables = course_soup.find_all('table')
                        for table in all_tables:
                            # Skip if already processed in cf-course
                            if any(table in cf.find_all('table') for cf in cf_courses):
                                continue
                            rows = table.find_all('tr')
                            for row in rows:
                                cells = row.find_all('td')
                                if len(cells) >= 2:
                                    instructor = cells[1].get_text(strip=True)
                                    if instructor and instructor not in instructors:
                                        instructors.append(instructor)
                    else:
                        description = ""
                        credits = ""
                        hub_credit = []
                        instructors = []
                except Exception:
                    description = ""
                    credits = ""
                    hub_credit = []
                    instructors = []
                
                # Get all text content from this link
                full_text = link.get_text(strip=True)
                
                # Try to find title (usually the first line or in a strong/bold element)
                title = ""
                strong_tag = link.find('strong')
                if strong_tag:
                    title = strong_tag.get_text(strip=True)
                else:
                    # Use link text as title
                    title = full_text
                
                # Parse title to separate course code and name
                course_code = ""
                course_name = ""
                if title and ':' in title:
                    parts = title.split(':', 1)
                    course_code = parts[0].strip()
                    course_name = parts[1].strip()
                else:
                    course_code = title if title else ""
                
                # Split college (first 3 characters) from course code
                college = ""
                if course_code and len(course_code) >= 3:
                    college = course_code[:3]
                    course_code = course_code[3:].strip()
                
                # Extract required courses using Scraper
                try:
                    required_courses = scrape_prerequisites(description)
                except Exception:
                    required_courses = []
                
                # Create course object for each link
                course_obj = {
                    'college': college,
                    'course_code': course_code,
                    'course_name': course_name,
                    'description': description,
                    'required_courses': required_courses,
                    'credits': credits,
                    'hub_credit': hub_credit,
                    'instructors': instructors,
                    'link': f"https://www.bu.edu{href}"
                }
                courses.append(course_obj)
        return courses
    except Exception as e:
        print(f"Failed to process {page_url}: {e}")
        return []

# Function to create course objects from max_paginated_urls
def create_college_course(max_paginated_urls, limit=None):
    all_courses = []
    for max_url in max_paginated_urls:
        # Extract base and max_value
        match = re.match(r"(https://www\.bu\.edu/academics/[a-z]+/courses/)(\d+)", max_url)
        if not match:
            continue
        base_url, max_value = match.groups()
        max_value = int(max_value)
        
        # Visit each page from max down to 0
        for n in range(1, max_value + 1, 1):
            if limit and len(all_courses) >= limit:
                return all_courses
            page_url = f"{base_url}{n}/"
            courses = process_course_page(page_url)
            all_courses.extend(courses)
            print(f"Processed {page_url}, found {len(courses)} courses.")
    return all_courses

# Create all course objects and filter out those without course names
courses = create_college_course(max_paginated_urls, limit=None)
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

