from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('contacts/', views.contacts, name='contacts'),
    path('contacts/create/', views.contact_create, name='contact-create'),
    path('settings/', views.settings, name='settings'),
    path('buttons/', views.buttons, name='buttons'),
]