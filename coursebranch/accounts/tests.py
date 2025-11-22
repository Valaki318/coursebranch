from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings
from django.core.files.base import ContentFile
from django.contrib.messages import get_messages
import json
import os

from .models import Profile
from .views import get_colleges_and_majors


# -------------------------
#   MODEL + SIGNAL TESTS
# -------------------------
class ProfileModelTests(TestCase):

    def test_profile_created_on_user_creation(self):
        """A Profile should automatically be created for each new User."""
        user = User.objects.create_user(username='testuser', password='pass123')
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_profile_str_representation(self):
        user = User.objects.create_user(username='john', password='pass123')
        profile = user.profile
        self.assertEqual(str(profile), "john's Profile")

    def test_profile_saved_on_user_save(self):
        """Saving the user should also save the profile (due to signal)."""
        user = User.objects.create_user(username='testuser2', password='pass123')
        profile = user.profile
        profile.bio = "Old bio"
        profile.save()

        # modify user
        user.first_name = "Bob"
        user.save()  # triggers save_user_profile signal

        profile.refresh_from_db()
        self.assertEqual(profile.bio, "Old bio")  # unchanged but saved without errors


# -------------------------
#   UTILITY FUNCTION TEST
# -------------------------
class GetCollegesMajorsTests(TestCase):

    def setUp(self):
        # Fake a bu_courses.json file in BASE_DIR
        self.test_json_path = os.path.join(settings.BASE_DIR, "bu_courses.json")
        sample_data = [
            {"course_code": "CAS CS 101"},
            {"course_code": "CAS MA 225"},
            {"course_code": "ENG EK 125"},
        ]
        with open(self.test_json_path, "w") as f:
            json.dump(sample_data, f)

    def tearDown(self):
        if os.path.exists(self.test_json_path):
            os.remove(self.test_json_path)

    def test_get_colleges_and_majors(self):
        data = get_colleges_and_majors()
        self.assertIn("CAS", data)
        self.assertIn("ENG", data)
        self.assertListEqual(sorted(data["CAS"]), ["CS", "MA"])
        self.assertListEqual(sorted(data["ENG"]), ["EK"])


# -------------------------
#   AUTH VIEWS TESTS
# -------------------------
class AuthViewsTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_signup_creates_user_and_profile(self):
        response = self.client.post(reverse('signup'), {
            "username": "newuser",
            "password1": "Testpass123",
            "password2": "Testpass123"
        })
        self.assertRedirects(response, reverse('home'))

        user = User.objects.get(username="newuser")
        self.assertTrue(Profile.objects.filter(user=user).exists())


    def test_signup_invalid(self):
        response = self.client.post(reverse('signup'), {
            "username": "bad user name",   # invalid: contains spaces
            "password1": "short",
            "password2": "shorter"          # mismatch
            })
    
        # stays on page, no redirect
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors)
        def test_login_view(self):
            User.objects.create_user("test", password="pass123")
            response = self.client.post(reverse('login'), {
                "username": "test",
                "password": "pass123",
                })
            self.assertRedirects(response, reverse('home'))

    def test_logout_view(self):
        user = User.objects.create_user("logoutuser", password="pass123")
        self.client.login(username="logoutuser", password="pass123")

        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))


    def test_login_invalid(self):
        response = self.client.post(reverse('login'), {
            "username": "nobody",
            "password": "wrong"
        })
    
        # No redirect → stays on page
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    
    def test_logout_while_anonymous(self):
        self.client.logout()
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, reverse("login"))


# -------------------------
#   PROFILE VIEW TESTS
# -------------------------
class ProfileViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("jack", password="pass123")
        self.client.login(username="jack", password="pass123")

    def test_profile_view_requires_login(self):
        # Logout first
        self.client.logout()

        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)  # redirects to login
        self.assertIn("/login", response["Location"])

    def test_profile_view_loads(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("profile", response.context)
        self.assertIn("colleges_data", response.context)

    def test_profile_update(self):
        response = self.client.post(reverse("profile"), {
            "bio": "Hello world",
            "college": "CAS",
            "major": "CS",
            "graduation_year": "2027"
        })

        self.assertRedirects(response, reverse("profile"))

        profile = self.user.profile
        profile.refresh_from_db()

        self.assertEqual(profile.bio, "Hello world")
        self.assertEqual(profile.college, "CAS")
        self.assertEqual(profile.major, "CS")
        self.assertEqual(profile.graduation_year, 2027)

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Profile updated!" in str(m) for m in messages))

    
    def test_profile_auto_created_in_view(self):
        self.user.profile.delete()
    
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
    
        # profile should be recreated by the view
        self.assertTrue(Profile.objects.filter(user=self.user).exists())
    

    def test_profile_view_colleges_data_is_valid_json(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
    
        data = response.context["colleges_data"]
        # Ensure JSON is parseable
        parsed = json.loads(data)
        self.assertIsInstance(parsed, dict)


    def test_home_view(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
