# CourseBranch

CourseBranch is a Django web application for exploring course catalogs, visualizing prerequisite trees, managing students, and reviewing courses. It includes an interactive, Obsidian-style force-directed graph of all courses and their prerequisite relationships.

---

## Features

### Course Catalog
- Upload a CSV to automatically populate:
  - Courses  
  - Instructors  
  - Credits  
  - Descriptions  
  - Prerequisite relationships
- Each course has its own detail page.

### Interactive Prerequisite Graph
- Drag-and-drop force-directed PyVis graph (like Obsidian Canvas)
- Hover tooltips with course information
- Click a node → goes to the course’s detail page
- “Back to Graph” button on each course page

### User Accounts
- Signup, login, logout
- Profile page for:
  - Major
  - Bio
  - Graduation year

### Institutions
- Auto-created **University** + **College** for testing
- Catalog uploads are attached to a College

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/Valaki318/coursebranch.git
cd coursebranch
```
### 2. Create virtual environment (recommended)
```bash
python3 -m venv .venv
source .venv/bin/activate
```
### 3. Install dependencies
```bash
pip install django pyvis
```
### 4. Apply migrations
```bash
python manage.py migrate
```
### 5. Create an optional admin account
```bash
python manage.py createsuperuser
```
### 6. Run the server
```bash
python manage.py runserver
```

### Project Structure
``` swift
accounts/
    models.py
    views.py
    templates/accounts/
catalog/
    models.py
    views.py
    templates/catalog/
coursebranch/
    settings.py
    urls.py
templates/
static/
db.sqlite3
```

### CSV Catalog Upload
/catalog/upload/

### CSV Format
``` swift
code,name,description,instructor,credits,prerequisites
CS101,Intro to CS,Learn fundamentals,Dr. Smith,3,
CS235,Data Structures,Study DS and algos,Dr. Williams,3,CS101
CS330,Algorithms,Advanced algorithms,Prof Davis,3,CS235

    prerequisites is ;-separated

    Order does not matter

    A second parsing pass automatically links prereqs
```
### Graph Visualization
``` swift
Visit:
/catalog/tree/
Graph features:

Fully draggable

Zoom / pan

Animated springs (force-directed)

Colored nodes

Click to open course details

Links show prerequisites (directed edges)
```
### User Features
``` swift
/signup/ — Create account
/login/ — Log in
/logout/ — Log out
/profile/ — Edit bio, major, graduation year
```
