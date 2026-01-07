from django.urls import path
from django.contrib.auth import views as authViews
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('upload/', views.UploadView.as_view(), name='upload'),
    path('login/', authViews.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', authViews.LogoutView.as_view(next_page='login'), name='logout'),
]