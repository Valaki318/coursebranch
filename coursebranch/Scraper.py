import spacy
import re

nlp = spacy.load("en_core_web_sm")

"""Code used NLP to extract prerequisites from course descriptions."""

def scrape_prerequisites(text):

    # Pattern for course codes (with or without space between dept and number, and multiple numbers)
    course_code_pattern = re.compile(r"(?:[A-Z]{2,6}\s+)?([A-Z]{2,4})\s*([0-9]{3}(?:/[0-9]{3})*)")

    # Find prerequisites (requirements) as a flat list and normalize course codes
    prereq_match = re.search(r"Prerequisites?:\s*([^.]+)", text, re.IGNORECASE)
    requirements = []
    if prereq_match:
        prereq_str = prereq_match.group(1)
        # If 'first year writing seminar' is mentioned, add CC 101 and WR 120
        if 'first year writing seminar' in prereq_str.lower():
            for fyws in ["CC 101", "WR 120"]:
                if fyws not in requirements:
                    requirements.append(fyws)
        # Remove parentheses
        prereq_str = re.sub(r"[()]", "", prereq_str)
        # Split by 'or', 'and', '&', ',', or ';'
        reqs = re.split(r"\s*(?:or|and|&|,|;)\s*", prereq_str, flags=re.IGNORECASE)

        for req in reqs:
            req = req.strip()
            if "equivalent" in req.lower():
                continue
            match = course_code_pattern.search(req)
            if match:
                dept, codes = match.groups()
                # Remove school prefix if present (e.g., 'CAS CS' -> 'CS')
                if len(dept) > 2 and dept[-2:].isalpha():
                    dept = dept[-2:]
                # Only include department codes with at most two letters
                if len(dept) <= 2:
                    for code in codes.split('/'):
                        val = f"{dept} {code}"
                        if val not in requirements:
                            requirements.append(val)
    return requirements
