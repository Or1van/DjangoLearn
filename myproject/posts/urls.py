from django.urls import path
from . import views #add this line to import views.py

urlpatterns = [
    path('', views.post_list,),     #url for homepage in views.py
]