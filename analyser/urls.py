from django.urls import path
from .views import marks_analyser

urlpatterns = [
    path('', marks_analyser, name='marks_analyser'),
]
