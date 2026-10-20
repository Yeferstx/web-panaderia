from django.contrib.auth import views as auth_views
from django.urls import path

urlpatterns = [
    path(
        "ingresar/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
]
