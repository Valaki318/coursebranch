from django.urls import path
from . import views

urlpatterns = [
    path('', views.catalog_view, name='catalog'),
    path('tree/', views.course_tree_view, name='course_tree'),
    path('tree/data/', views.course_graph_json, name='course_graph_data'),
    path('course/<str:code>/', views.course_detail_view, name='course_detail'),
    path("graph.json", views.course_graph_json, name="course_graph_json"),
]
