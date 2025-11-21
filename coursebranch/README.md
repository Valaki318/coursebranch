# CourseBranch

A Django web application for course management and reviews.

## Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/Valaki318/coursebranch.git
cd coursebranch
```

2. Install Django (if not already installed):
```bash
pip install django
```

3. Run database migrations:
```bash
python manage.py migrate
```

4. Create a superuser account (optional, for admin access):
```bash
python manage.py createsuperuser
```

5. Start the development server:
```bash
python manage.py runserver
```

6. Open your browser and navigate to:
   - Main site: `http://localhost:8000/`
   - Admin panel: `http://localhost:8000/admin/`

## Project Structure

- `accounts/` - User authentication and profile management
- `coursebranch/` - Main project settings and configuration
- `db.sqlite3` - SQLite database (not included in repository)

## Usage

1. Sign up for a new account at `/signup/`
2. Log in at `/login/`
3. Access your profile at `/profile/` 
