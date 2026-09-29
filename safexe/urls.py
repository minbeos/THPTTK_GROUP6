from django.contrib import admin
from django.urls import path, include

try:
    from safexe.core import urls as core_urls
except ImportError:
    from core import urls as core_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(core_urls)),
]
