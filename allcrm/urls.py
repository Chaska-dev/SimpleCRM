from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from crm.views import root_redirect

handler404 = 'crm.views.custom_404'

urlpatterns = [
    path('admin/', admin.site.urls),
    # Root: one-hop redirect to the right place (dashboard if logged in,
    # login otherwise). See crm.views.root_redirect.
    path('', root_redirect, name='root'),
    path('', include('crm.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)