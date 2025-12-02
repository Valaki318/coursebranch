from django.urls import path
from . import views

urlpatterns = [
    path('', views.catalog_view, name='catalog'),
    path('tree/', views.course_tree_view, name='course_tree'),
    path('tree/data/', views.course_graph_json, name='course_graph_data'),
    path('course/<str:code>/', views.course_detail_view, name='course_detail'),
    path("graph.json", views.course_graph_json, name="course_graph_json"),
    path("add_course/", views.add_course, name="add_course"),
    path("remove_course/", views.remove_course, name="remove_course"),
    path("course/<str:code>/review/", views.create_review, name="create_review")

]
