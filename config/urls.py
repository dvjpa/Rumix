from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('animais/', include(('animais.urls', 'animais'), namespace='animais')),
    path('fazendas/', include(('fazendas.urls', 'fazendas'), namespace='fazendas')),
    path('usuarios/', include(('usuarios.urls', 'usuarios'), namespace='usuarios')),
    path('eventos/', include(('eventos.urls', 'eventos'), namespace='eventos')),
    path('marketplace/', include(('marketplace.urls', 'marketplace'), namespace='marketplace')), # 🛒 Atualizado com namespace
    path('', include(('rumix.urls', 'rumix'), namespace='rumix')), # Mantido no final para capturar a rota raiz
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)