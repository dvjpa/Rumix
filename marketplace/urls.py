from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    # Anúncios
    path('', views.marketplace_home, name='home'),
    path('novo/', views.create_announcement, name='create'),
    path('anuncio/<int:pk>/', views.announcement_detail, name='detail'),  # 👈 Rota que estava faltando!
    path('leilao/<int:pk>/lance/', views.place_bid, name='place_bid'),
    
    # Gerenciamento de Itens
    path('meus-itens/', views.item_list, name='item_list'),
    path('meus-itens/novo/', views.create_item, name='create_item'),

    # Pagamentos
    path('pagamento/pix/<int:pk>/', views.checkout_pix, name='checkout_pix'),
    path('webhook/mercadopago/', views.mercadopago_webhook, name='mercadopago_webhook'),
]
