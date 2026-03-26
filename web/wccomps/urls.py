"""URL configuration for ECS 198F authentication bot."""

from django.urls import path

from core import oauth, views

urlpatterns = [
    path("health/", views.health_check, name="health_check"),
    # OAuth flow
    path("auth/login/", oauth.oauth_login, name="oauth_login"),
    path("auth/callback/", oauth.oauth_callback, name="oauth_callback"),
    path("auth/logout/", oauth.oauth_logout, name="oauth_logout"),
    # ECS 198F student authentication
    path("auth/198f", views.auth_198f_initiate, name="auth_198f_initiate"),
    path("auth/198f-callback", views.auth_198f_callback, name="auth_198f_callback"),
]
