from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from catalog.models import University, College, Course
from catalog.views import _get_major_query, _derive_course_level
from django.db.models import Q
import json


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

    def test_major_matches_CS_department(self):
        c = create_course(self.college, code="CAS CS 101")
        q = _get_major_query("Computer Science")
        results = Course.objects.filter(q)
        self.assertIn(c, results)

    def test_major_short_form(self):
        c = create_course(self.college, code="CS 200")
        q = _get_major_query("CS")
        results = Course.objects.filter(q)
        self.assertIn(c, results)

    def test_major_fallback_token_search(self):
        c = create_course(self.college, code="PH 300", name="Political Science Theory")
        q = _get_major_query("Political Science")  # Should token-match name
        results = Course.objects.filter(q)
        self.assertIn(c, results)

    def test_nonmatching_major(self):
        create_course(self.college, code="MA 101")
        q = _get_major_query("Biology")
        results = Course.objects.filter(q)
        self.assertEqual(results.count(), 0)


###################################
# catalog_view Tests
###################################

class CatalogViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.uni = create_university("BU")
        self.college = create_college(self.uni, "CAS")

        self.cs101 = create_course(self.college, code="CAS CS 101")
        self.ma101 = create_course(self.college, code="CAS MA 101")

    def test_catalog_view_all(self):
        url = reverse("catalog")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["courses"]), 2)

    def test_catalog_view_major_filter_anonymous(self):
        url = reverse("catalog") + "?filter=major"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["courses"]), 0)  # anon user has no major

    def test_catalog_view_major_filter_authenticated(self):
        # Create user w/ profile
        user = User.objects.create_user("jake", password="pass")
        user.profile.major = "CS"
        user.profile.college = "CAS"
        user.profile.save()

        self.client.login(username="jake", password="pass")

        url = reverse("catalog") + "?filter=major"
        resp = self.client.get(url)

        # Should return only CS courses
        self.assertIn(self.cs101, resp.context["courses"])
        self.assertNotIn(self.ma101, resp.context["courses"])


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

    def test_course_detail_view(self):
        url = reverse("course_detail", args=["CS 101"])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["course"], self.cs101)
        self.assertIn(self.cs201, resp.context["postreqs"])


###################################
# course_tree_view Tests
###################################

class CourseTreeViewTests(TestCase):
    def test_tree_page_renders(self):
        c = Client()
        resp = c.get(reverse("course_tree"))
        self.assertEqual(resp.status_code, 200)


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



#############################
# Helper Factory Functions
#############################

def create_university(name="Test Uni"):
    return University.objects.create(name=name)

def create_college(university=None, name="Engineering"):
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

    def test_major_matches_CS_department(self):
        c = create_course(self.college, code="CAS CS 101")
        q = _get_major_query("Computer Science")
        results = Course.objects.filter(q)
        self.assertIn(c, results)

    def test_major_short_form(self):
        c = create_course(self.college, code="CS 200")
        q = _get_major_query("CS")
        results = Course.objects.filter(q)
        self.assertIn(c, results)

    def test_major_fallback_token_search(self):
        c = create_course(self.college, code="PH 300", name="Political Science Theory")
        q = _get_major_query("Political Science")  # Should token-match name
        results = Course.objects.filter(q)
        self.assertIn(c, results)

    def test_nonmatching_major(self):
        create_course(self.college, code="MA 101")
        q = _get_major_query("Biology")
        results = Course.objects.filter(q)
        self.assertEqual(results.count(), 0)


###################################
# catalog_view Tests
###################################

class CatalogViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.uni = create_university("BU")
        self.college = create_college(self.uni, "CAS")

        self.cs101 = create_course(self.college, code="CAS CS 101")
        self.ma101 = create_course(self.college, code="CAS MA 101")

    def test_catalog_view_all(self):
        url = reverse("catalog")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["courses"]), 2)

    def test_catalog_view_major_filter_anonymous(self):
        url = reverse("catalog") + "?filter=major"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["courses"]), 0)  # anon user has no major

    def test_catalog_view_major_filter_authenticated(self):
        # Create user w/ profile
        user = User.objects.create_user("jake", password="pass")
        user.profile.major = "CS"
        user.profile.college = "CAS"
        user.profile.save()

        self.client.login(username="jake", password="pass")

        url = reverse("catalog") + "?filter=major"
        resp = self.client.get(url)

        # Should return only CS courses
        self.assertIn(self.cs101, resp.context["courses"])
        self.assertNotIn(self.ma101, resp.context["courses"])


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

    def test_course_detail_view(self):
        url = reverse("course_detail", args=["CS 101"])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["course"], self.cs101)
        self.assertIn(self.cs201, resp.context["postreqs"])


###################################
# course_tree_view Tests
###################################

class CourseTreeViewTests(TestCase):
    def test_tree_page_renders(self):
        c = Client()
        resp = c.get(reverse("course_tree"))
        self.assertEqual(resp.status_code, 200)


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

########################################
# course_graph_json Tests
########################################

class CourseGraphJSONTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.college = create_college()

    def _json(self, resp):
        return resp.json()["elements"]

    def test_no_major_fallback_to_first_20(self):
        # Create 25 courses to check truncation behavior
        for i in range(25):
            create_course(self.college, code=f"CS {100+i}", name=f"Course{i}")

        resp = self.client.get(reverse("course_graph_json"))
        self.assertEqual(resp.status_code, 200)

        data = self._json(resp)

        # Should only contain 20 nodes
        self.assertEqual(len(data["nodes"]), 20)

    def test_major_query_filtering(self):
        cs101 = create_course(self.college, code="CS 101", name="Intro")
        ma101 = create_course(self.college, code="MA 101", name="Math")

        resp = self.client.get(reverse("course_graph_json") + "?major=CS")
        data = self._json(resp)

        ids = {n["data"]["id"] for n in data["nodes"]}
        self.assertIn("CS 101", ids)
        self.assertNotIn("MA 101", ids)

    def test_profile_major_fallback_when_no_query_param(self):
        user = User.objects.create_user("jack", password="pass")
        user.profile.major = "CS"
        user.profile.save()

        self.client.login(username="jack", password="pass")

        cs101 = create_course(self.college, code="CS 101")
        ma101 = create_course(self.college, code="MA 101")

        resp = self.client.get(reverse("course_graph_json"))
        data = self._json(resp)

        ids = {n["data"]["id"] for n in data["nodes"]}
        self.assertIn("CS 101", ids)
        self.assertNotIn("MA 101", ids)

    def test_bfs_prereq_traversal(self):
        """
        cs201 -> cs101
        If cs201 matches the filter, the graph should include cs101 as well.
        """
        cs101 = create_course(self.college, code="CS 101")
        cs201 = create_course(self.college, code="CS 201")
        cs201.prerequisites.add(cs101)

        resp = self.client.get(reverse("course_graph_json") + "?major=CS")
        data = self._json(resp)

        node_ids = {n["data"]["id"] for n in data["nodes"]}
        self.assertIn("CS 101", node_ids)  # BFS pulled prereq
        self.assertIn("CS 201", node_ids)

        # Correct edge direction: prereq → course
        edges = {(e["data"]["source"], e["data"]["target"]) for e in data["edges"]}
        self.assertIn(("CS 101", "CS 201"), edges)

    def test_json_node_structure_and_levels(self):
        cs450 = create_course(self.college, code="CS 450", name="Systems")

        resp = self.client.get(reverse("course_graph_json") + "?major=CS")
        data = self._json(resp)

        # Only node is cs450
        node = data["nodes"][0]["data"]

        self.assertEqual(node["id"], "CS 450")
        self.assertEqual(node["name"], "Systems")
        self.assertEqual(node["label"], "CS 450")
        self.assertEqual(node["level"], _derive_course_level("CS 450"))

    def test_empty_database_returns_empty_graph(self):
        # Ensure database really empty
        Course.objects.all().delete()

        resp = self.client.get(reverse("course_graph_json") + "?major=CS")
        data = self._json(resp)

        self.assertEqual(data["nodes"], [])
        self.assertEqual(data["edges"], [])

