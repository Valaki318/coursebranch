from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from catalog.models import University, College, Course, Review
from catalog.views import _get_major_query, _derive_course_level
from django.db.models import Q
from unittest.mock import patch
import json


#############################
# Helper Factory Functions
#############################

def create_university(name="Test Uni"):
    return University.objects.create(name=name)

def create_college(university=None, name="CAS"):
    university = university or create_university()
    return College.objects.create(university=university, name=name)

def create_course(college=None, code="CS 101", name="Intro CS", desc="x", instructor="Bob", credits=4):
    college = college or create_college()
    return Course.objects.create(
        college=college,
        code=code,
        name=name,
        description=desc,
        instructor=instructor,
        credits=credits
    )

def create_logged_in_user(client, username="testuser", password="pass", major=None, college=None):
    """Helper to create a user and log them in."""
    user = User.objects.create_user(username, password=password)
    if major:
        user.profile.major = major
    if college:
        user.profile.college = college
    if major or college:
        user.profile.save()
    client.login(username=username, password=password)
    return user


###################################
# Model Relationship Tests
###################################

class ModelTests(TestCase):
    def test_university_college_relationship(self):
        u = create_university("Boston University")
        c = create_college(university=u, name="CAS")

        self.assertEqual(c.university, u)
        self.assertEqual(u.colleges.count(), 1)

    def test_course_creation(self):
        c = create_course(code="CAS CS 111", name="CS1")
        self.assertEqual(str(c), "CAS CS 111: CS1")

    def test_course_prerequisites(self):
        college = create_college()
        c1 = create_course(college, code="CS 101")
        c2 = create_course(college, code="CS 201")

        c2.prerequisites.add(c1)

        self.assertIn(c1, c2.prerequisites.all())
        self.assertIn(c2, c1.required_for.all())


###################################
# _get_major_query Tests
###################################

class GetMajorQueryTests(TestCase):
    def setUp(self):
        self.college = create_college()

    def test_empty_major_returns_empty_query(self):
        q = _get_major_query("")
        self.assertEqual(q, Q())

    def test_none_major_returns_empty_query(self):
        q = _get_major_query(None)
        self.assertEqual(q, Q())

    @patch('catalog.views.get_major_requirements')
    def test_major_with_mocked_requirements(self, mock_get_major):
        """Test that _get_major_query builds correct query from major requirements."""
        mock_get_major.return_value = {
            'required_courses': ['CAS CS 101', 'CAS CS 201']
        }
        c = create_course(self.college, code="CAS CS 101")
        
        q = _get_major_query("Computer Science")
        results = Course.objects.filter(q)
        self.assertIn(c, results)

    @patch('catalog.views.get_major_requirements')
    def test_major_fallback_to_code_mapping(self, mock_get_major):
        """Test fallback to MAJOR_CODES when no requirements found."""
        mock_get_major.return_value = None
        c = create_course(self.college, code="CAS CS 101")
        
        q = _get_major_query("Computer Science")
        results = Course.objects.filter(q)
        self.assertIn(c, results)

    @patch('catalog.views.get_major_requirements')
    def test_short_code_fallback(self, mock_get_major):
        """Test that short codes like 'PY' work as fallback."""
        mock_get_major.return_value = None
        c = create_course(self.college, code="CAS PY 101")
        
        q = _get_major_query("PY")
        results = Course.objects.filter(q)
        self.assertIn(c, results)

    @patch('catalog.views.get_major_requirements')
    def test_nonmatching_major(self, mock_get_major):
        """Test that unrelated courses are not returned."""
        mock_get_major.return_value = None
        create_course(self.college, code="CAS MA 101", name="Math Course")
        
        q = _get_major_query("Biology")
        results = Course.objects.filter(q)
        self.assertEqual(results.count(), 0)


###################################
# _derive_course_level Tests
###################################

class DeriveCourseLevelTests(TestCase):
    def test_basic_levels(self):
        self.assertEqual(_derive_course_level("CS 101"), "100")
        self.assertEqual(_derive_course_level("CS 250"), "200")
        self.assertEqual(_derive_course_level("CS 999"), "500")  # capped at 500
        self.assertEqual(_derive_course_level("CS 50"), "OTHER")
        self.assertEqual(_derive_course_level("NONSENSE"), "OTHER")

    def test_empty_code(self):
        self.assertEqual(_derive_course_level(""), "OTHER")


###################################
# catalog_view Tests
###################################

class CatalogViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.uni = create_university("BU")
        self.college = create_college(self.uni, "CAS")
        self.cs101 = create_course(self.college, code="CAS CS 101", name="Intro CS")
        self.ma101 = create_course(self.college, code="CAS MA 101", name="Intro Math")

    def test_catalog_view_requires_login(self):
        """Anonymous users should be redirected to login."""
        url = reverse("catalog")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)  # Redirect to login

    def test_catalog_view_all_authenticated(self):
        """Logged in user sees all courses."""
        create_logged_in_user(self.client)
        url = reverse("catalog")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["courses"]), 2)

    def test_catalog_view_major_filter_no_major_set(self):
        """User with no major set, filter=major returns empty."""
        create_logged_in_user(self.client)
        url = reverse("catalog") + "?filter=major"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["courses"]), 0)

    @patch('catalog.views._get_major_query')
    def test_catalog_view_major_filter_authenticated(self, mock_query):
        """User with major set sees filtered courses."""
        # Mock the query to return only CS courses
        mock_query.return_value = Q(code__icontains="CS")
        
        create_logged_in_user(self.client, username="jake", major="Computer Science", college="CAS")

        url = reverse("catalog") + "?filter=major"
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.cs101, resp.context["courses"])
        self.assertNotIn(self.ma101, resp.context["courses"])

    def test_catalog_view_search_by_code(self):
        """Search filters by course code."""
        create_logged_in_user(self.client)
        url = reverse("catalog") + "?q=CS"
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.cs101, resp.context["courses"])
        self.assertNotIn(self.ma101, resp.context["courses"])

    def test_catalog_view_search_by_name(self):
        """Search filters by course name."""
        create_logged_in_user(self.client)
        url = reverse("catalog") + "?q=Math"
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.ma101, resp.context["courses"])
        self.assertNotIn(self.cs101, resp.context["courses"])


###################################
# course_detail_view Tests
###################################

class CourseDetailTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.college = create_college()
        self.cs101 = create_course(self.college, code="CS 101")
        self.cs201 = create_course(self.college, code="CS 201")
        self.cs201.prerequisites.add(self.cs101)

    def test_course_detail_requires_login(self):
        """Anonymous users should be redirected."""
        url = reverse("course_detail", args=["CS 101"])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    def test_course_detail_view_authenticated(self):
        """Logged in user can view course details."""
        create_logged_in_user(self.client)
        url = reverse("course_detail", args=["CS 101"])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["course"], self.cs101)
        self.assertIn(self.cs201, resp.context["postreqs"])

    def test_course_detail_with_completed_courses(self):
        """User with completed courses sees them in context."""
        user = create_logged_in_user(self.client)
        user.profile.completed_courses.add(self.cs101)

        url = reverse("course_detail", args=["CS 201"])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["authenticated"])
        self.assertIn("CS 101", resp.context["completed_codes"])


###################################
# course_tree_view Tests
###################################

class CourseTreeViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_tree_page_requires_login(self):
        resp = self.client.get(reverse("course_tree"))
        self.assertEqual(resp.status_code, 302)

    def test_tree_page_renders_authenticated(self):
        create_logged_in_user(self.client)
        resp = self.client.get(reverse("course_tree"))
        self.assertEqual(resp.status_code, 200)


###################################
# course_graph_json Tests
###################################

class CourseGraphJSONTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.college = create_college()

    def _json(self, resp):
        return resp.json()["elements"]

    def test_graph_requires_login(self):
        resp = self.client.get(reverse("course_graph_json"))
        self.assertEqual(resp.status_code, 302)

    def test_no_major_fallback_to_first_20(self):
        create_logged_in_user(self.client)
        # Create 25 courses with codes that won't match any major
        for i in range(25):
            create_course(self.college, code=f"XX {100+i}", name=f"Course{i}")

        resp = self.client.get(reverse("course_graph_json"))
        self.assertEqual(resp.status_code, 200)
        data = self._json(resp)
        self.assertEqual(len(data["nodes"]), 20)

    @patch('catalog.views._get_major_query')
    def test_major_query_filtering(self, mock_query):
        """Test that major query param filters courses."""
        mock_query.return_value = Q(code__icontains="CS")
        
        create_logged_in_user(self.client)
        cs101 = create_course(self.college, code="CAS CS 101", name="Intro")
        ma101 = create_course(self.college, code="CAS MA 101", name="Math")

        resp = self.client.get(reverse("course_graph_json") + "?major=CS")
        data = self._json(resp)

        ids = {n["data"]["id"] for n in data["nodes"]}
        self.assertIn("CAS CS 101", ids)
        self.assertNotIn("CAS MA 101", ids)

    @patch('catalog.views._get_major_query')
    def test_profile_major_fallback_when_no_query_param(self, mock_query):
        """Test that user's profile major is used when no query param."""
        mock_query.return_value = Q(code__icontains="CS")
        
        create_logged_in_user(self.client, username="jack", major="Computer Science", college="CAS")

        cs101 = create_course(self.college, code="CAS CS 101")
        ma101 = create_course(self.college, code="CAS MA 101")

        resp = self.client.get(reverse("course_graph_json"))
        data = self._json(resp)

        ids = {n["data"]["id"] for n in data["nodes"]}
        self.assertIn("CAS CS 101", ids)
        self.assertNotIn("CAS MA 101", ids)

    @patch('catalog.views._get_major_query')
    def test_bfs_prereq_traversal(self, mock_query):
        """If cs201 matches filter, graph should include its prereq cs101."""
        mock_query.return_value = Q(code__icontains="CS")
        
        create_logged_in_user(self.client)
        cs101 = create_course(self.college, code="CAS CS 101")
        cs201 = create_course(self.college, code="CAS CS 201")
        cs201.prerequisites.add(cs101)

        resp = self.client.get(reverse("course_graph_json") + "?major=CS")
        data = self._json(resp)

        node_ids = {n["data"]["id"] for n in data["nodes"]}
        self.assertIn("CAS CS 101", node_ids)
        self.assertIn("CAS CS 201", node_ids)

        edges = {(e["data"]["source"], e["data"]["target"]) for e in data["edges"]}
        self.assertIn(("CAS CS 101", "CAS CS 201"), edges)

    @patch('catalog.views._get_major_query')
    def test_json_node_structure_and_levels(self, mock_query):
        mock_query.return_value = Q(code__icontains="CS")
        
        create_logged_in_user(self.client)
        cs450 = create_course(self.college, code="CAS CS 450", name="Systems")

        resp = self.client.get(reverse("course_graph_json") + "?major=CS")
        data = self._json(resp)

        node = data["nodes"][0]["data"]
        self.assertEqual(node["id"], "CAS CS 450")
        self.assertEqual(node["name"], "Systems")
        self.assertEqual(node["level"], "400")

    def test_empty_database_returns_empty_graph(self):
        create_logged_in_user(self.client)
        Course.objects.all().delete()

        resp = self.client.get(reverse("course_graph_json"))
        data = self._json(resp)

        self.assertEqual(data["nodes"], [])
        self.assertEqual(data["edges"], [])


###################################
# add_course / remove_course Tests
###################################

class AddRemoveCourseTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.college = create_college()
        self.cs101 = create_course(self.college, code="CS 101")

    def test_add_course_requires_login(self):
        url = reverse("add_course")
        resp = self.client.post(url, {"code": "CS 101"})
        self.assertEqual(resp.status_code, 302)

    def test_add_course(self):
        user = create_logged_in_user(self.client)
        url = reverse("add_course")
        resp = self.client.post(url, {"code": "CS 101"})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})
        self.assertIn(self.cs101, user.profile.completed_courses.all())

    def test_remove_course_requires_login(self):
        url = reverse("remove_course")
        resp = self.client.post(url, {"code": "CS 101"})
        self.assertEqual(resp.status_code, 302)

    def test_remove_course(self):
        user = create_logged_in_user(self.client)
        user.profile.completed_courses.add(self.cs101)

        url = reverse("remove_course")
        resp = self.client.post(url, {"code": "CS 101"})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})
        self.assertNotIn(self.cs101, user.profile.completed_courses.all())


###################################
# create_review Tests
###################################

class CreateReviewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.college = create_college()
        self.cs101 = create_course(self.college, code="CS 101")

    def test_create_review_requires_login(self):
        url = reverse("create_review", args=["CS 101"])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    def test_create_review_get(self):
        create_logged_in_user(self.client)
        url = reverse("create_review", args=["CS 101"])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["course"], self.cs101)

    def test_create_review_post(self):
        create_logged_in_user(self.client)
        url = reverse("create_review", args=["CS 101"])
        resp = self.client.post(url, {"rating": 5, "comment": "Great course!"})

        self.assertRedirects(resp, reverse("course_detail", args=["CS 101"]))
        self.assertEqual(self.cs101.reviews.count(), 1)
        review = self.cs101.reviews.first()
        self.assertEqual(review.rating, 5)  # Integer, not string
        self.assertEqual(review.comment, "Great course!")
