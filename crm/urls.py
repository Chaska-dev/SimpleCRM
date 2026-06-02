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
    path('contacts/<uuid:contact_uuid>/delete/', views.contact_delete, name='contact-delete'),
    path('contacts/bulk-delete/', views.contact_bulk_delete, name='contact-bulk-delete'),
    path('settings/', views.settings, name='settings'),
    path('import-export/', views.import_export, name='import-export'),
    path('buttons/', views.buttons, name='buttons'),
    path('api/companies/search/', views.company_search, name='company-search'),
    path('companies/', views.companies, name='companies'),
    path('companies/create/', views.company_create, name='company-create'),
    path('companies/<uuid:company_uuid>/edit/', views.company_edit, name='company-edit'),
    path('companies/<uuid:company_uuid>/delete/', views.company_delete, name='company-delete'),
    path('companies/bulk-delete/', views.company_bulk_delete, name='company-bulk-delete'),
    path('api/locations/countries/', views.country_search, name='country-search'),
    path('api/locations/states/', views.state_search, name='state-search'),
    path('api/locations/cities/', views.city_search, name='city-search'),
]