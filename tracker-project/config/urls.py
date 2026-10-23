from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from expenses import views as expense_views

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", expense_views.signup, name="signup"),
    path("", include("expenses.urls")),
]
