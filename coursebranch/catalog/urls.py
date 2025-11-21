from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_catalog_view, name='catalog_upload'),
    path('tree/', views.course_tree_index_view, name='catalog_tree'),
    path('tree/graph/', views.course_tree_view, name='catalog_graph'),
    path("course/<str:code>/", views.course_detail_view, name="course_detail"),
]

