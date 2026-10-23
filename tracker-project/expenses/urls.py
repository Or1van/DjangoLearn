from django.urls import path

from . import views

app_name = "expenses"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("transactions/", views.transaction_list, name="list"),
    path("add/", views.transaction_create, name="create"),
    path("<int:pk>/edit/", views.transaction_update, name="update"),
    path("<int:pk>/delete/", views.transaction_delete, name="delete"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/<int:pk>/edit/", views.category_update, name="category_update"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("stats/", views.stats, name="stats"),
    path("stats/data/", views.stats_api, name="stats_api"),
]
