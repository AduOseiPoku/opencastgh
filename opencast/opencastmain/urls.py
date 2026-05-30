from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = "OpenCastGH Admin"
admin.site.site_title = "OpenCastGH"
admin.site.index_title = "Platform Management"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('voting.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
