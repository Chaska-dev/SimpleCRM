from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf.urls.static import static
from django.conf import settings

handler404 = 'crm.views.custom_404'

urlpatterns = [
    path('admin/', admin.site.urls),
    # Empty path -> send users to the dashboard (which itself bounces to
    # /login/ if they're not authenticated, thanks to @login_required).
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    path('', include('crm.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)