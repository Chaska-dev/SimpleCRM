from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('contacts/', views.contacts, name='contacts'),
    path('contacts/create/', views.contact_create, name='contact-create'),
    path('contacts/<uuid:contact_uuid>/edit/', views.contact_edit, name='contact-edit'),
    path('settings/', views.settings, name='settings'),
    path('import-export/', views.import_export, name='import-export'),
    path('buttons/', views.buttons, name='buttons'),
]