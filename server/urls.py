from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.urls import path, re_path, include

schema_view = get_schema_view(
    openapi.Info(
        title="API",
        default_version="v1",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    re_path(r'^$', schema_view.with_ui('swagger', cache_timeout=0)),
    path('', include('app.urls'))
]