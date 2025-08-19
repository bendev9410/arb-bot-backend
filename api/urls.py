# api/urls.py

from django.urls import path
from .views import get_arb_results

urlpatterns = [
    path('arb/', get_arb_results, name='get_arb_results'),
]
