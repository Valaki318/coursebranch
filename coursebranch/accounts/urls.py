from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/courses', views.courses_view, name='completed_courses'),
    path('profile/courses/add', views.add_completed_courses_view, name='add_completed_courses'),
    path('profile/change-username', views.change_username_view, name='change_username'),
    path('profile/change-password', views.change_password_view, name='change_password'),
    path('', views.home_view, name='home'),
]
