import requests
from bs4 import BeautifulSoup
import json
from majorParser import scrape_major_requirements


def scrape_major_links(page_url):
    """
    Scrapes a page for major/program links following the format:
    <li class="mj">Program Name (<a href="/url/">Degree</a>)</li>
    
    Args:
        page_url: URL of the page to scrape
    
    Returns:
        List of dictionaries containing major information with keys:
        - 'name': The major/program name
        - 'degree': The degree type (BA, BS, etc.)
        - 'link': The full URL to the program page
    """
    try:
        response = requests.get(page_url)
        if response.status_code != 200:
            print(f"Failed to fetch {page_url}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all <li> elements with class="mj"
        major_items = soup.find_all('li', class_='mj')
        
        majors = []
        
        for item in major_items:
            # Get the full text of the li element
            full_text = item.get_text(strip=True)
            
            # Find the link within this li
            link_tag = item.find('a', href=True)
            
            if link_tag:
                # Extract degree type from link text
                degree = link_tag.get_text(strip=True)
                
                # Extract href
                href = link_tag['href']
                
                # Make the link absolute if it's relative
                if href.startswith('/'):
                    full_link = f"https://www.bu.edu{href}"
                elif href.startswith('http'):
                    full_link = href
                else:
                    full_link = f"https://www.bu.edu/{href}"
                
                # Extract the program name (everything before the link)
                # Remove the degree part in parentheses
                program_name = full_text
                if f"({degree})" in program_name:
                    program_name = program_name.replace(f"({degree})", "").strip()
                
                major_obj = {
                    'name': program_name,
                    'degree': degree,
                    'link': full_link
                }
                
                majors.append(major_obj)
                print(f"Found: {program_name} - {degree} - {full_link}")
        
        return majors
        
    except Exception as e:
        print(f"Error scraping {page_url}: {e}")
        return []


def create_major_objects_with_requirements(page_url):
    """
    Scrapes a page for all majors and creates objects with their required courses.
    
    Args:
        page_url: URL of the page containing major links
    
    Returns:
        List of dictionaries containing major information and required courses
    """
    # First, get all major links
    majors = scrape_major_links(page_url)
    
    # For each major, scrape the requirements
    major_objects = []
    
    for i, major in enumerate(majors):
        print(f"\nProcessing {i+1}/{len(majors)}: {major['name']} ({major['degree']})")
        
        # Get the required courses for this major
        required_courses = scrape_major_requirements(major['link'])
        
        # Create the complete major object
        major_obj = {
            'name': major['name'],
            'degree': major['degree'],
            'link': major['link'],
            'required_courses': required_courses
        }
        
        major_objects.append(major_obj)
        print(f"  Found {len(required_courses)} required courses")
    
    return major_objects


# Example usage
if __name__ == "__main__":
    url = "https://www.bu.edu/academics/degree-programs/"
    
    # Create major objects with their required courses
    major_objects = create_major_objects_with_requirements(url)
    
    print(f"\n\nTotal majors processed: {len(major_objects)}")
    
    # Save to JSON file
    if major_objects:
        with open('bu_majors.json', 'w', encoding='utf-8') as f:
            json.dump(major_objects, f, indent=2, ensure_ascii=False)
        print("Major data with requirements exported to bu_majors.json")
    
    # Show first example with requirements
    if major_objects:
        print("\nExample major object:")
        example = major_objects[0]
        print(f"  Name: {example['name']}")
        print(f"  Degree: {example['degree']}")
        print(f"  Link: {example['link']}")
        print(f"  Required Courses ({len(example['required_courses'])}):")
        for course in example['required_courses'][:5]:  # Show first 5
            print(f"    - {course}")
        if len(example['required_courses']) > 5:
            print(f"    ... and {len(example['required_courses']) - 5} more")
