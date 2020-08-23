"""thesis_django URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views
from thesis_ui import urls as thesis_ui_urls
from admin_tasks import urls as admin_tasks_urls

urlpatterns = [
    path('', include(thesis_ui_urls)),
    # path("accounts/", include("django.contrib.auth.urls")),
    path('accounts/login/', auth_views.LoginView.as_view()),
    path("admin-tasks/", include(admin_tasks_urls)),
    re_path(r"^celery-progress/", include("celery_progress.urls")),
    path('admin/', admin.site.urls),
]
