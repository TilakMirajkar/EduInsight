from django.urls import path
from scraper import views

urlpatterns = [
    path("", views.index, name='index'),  # index page
    path("marksscraper/", views.MarksScraper, name='marks_scraper'),  # Scraper View
    path('download/<str:filename>/', views.download_file, name='download_file'),  # Download File View
    path("working/", views.Working, name='working')  # How it works view
]
