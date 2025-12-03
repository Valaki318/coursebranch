import requests
from bs4 import BeautifulSoup
import re


def scrape_major_requirements(page_url):
    try:
        response = requests.get(page_url)
        if response.status_code != 200:
            print(f"Failed to fetch {page_url}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        course_codes = []
        
        # Look for sections containing "Requirements" or "Requirement"
        # This could be in headings like h2, h3, or section titles
        requirements_sections = []
        
        # Find all headings that might indicate requirements
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            heading_text = heading.get_text(strip=True)
            if 'requirement' in heading_text.lower():
                # Get the content following this heading until the next heading
                requirements_sections.append(heading.parent)
        
        # If no specific requirements section found, search the whole page
        if not requirements_sections:
            requirements_sections = [soup]
        
        # Pattern to match course codes (e.g., CAS CS 112, ENG EK 125, etc.)
        # Matches: 2-3 uppercase letters, space, 2-3 uppercase letters, space, 3-4 digits
        course_pattern = re.compile(r'\b([A-Z]{2,3}\s+[A-Z]{2,3}\s+\d{3,4})\b')
        
        for section in requirements_sections:
            # Get all text from this section
            section_text = section.get_text()
            
            # Find all course codes in the section
            matches = course_pattern.findall(section_text)
            
            for match in matches:
                if match not in course_codes:
                    course_codes.append(match)
                    print(f"Found course: {match}")
        
        return course_codes
        
    except Exception as e:
        print(f"Error scraping {page_url}: {e}")
        return []


# Example usage
if __name__ == "__main__":
    # Example URL - replace with actual major page
    test_url = "https://www.bu.edu/academics/cas/programs/computer-science/ba-in-computer-science/"
    
    courses = scrape_major_requirements(test_url)
    
    print(f"\nTotal course codes found: {len(courses)}")
    print("\nCourse codes:")
    for course in courses:
        print(f"  - {course}")
