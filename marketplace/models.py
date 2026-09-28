from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

class ListingType(models.TextChoices):
    SALE = 'SALE', 'Venda'
    EXCHANGE = 'EXCHANGE', 'Troca'
    AUCTION = 'AUCTION', 'Leilão'


class ListingStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Ativo'
    COMPLETED = 'COMPLETED', 'Concluído'
    CANCELLED = 'CANCELLED', 'Cancelado'


class Item(models.Model):
    """Item a ser negociado no projeto Rumix"""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='items')
    title = models.CharField('Título', max_length=200)
    description = models.TextField('Descrição')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Announcement(models.Model):
    """Anúncio principal (Venda, Troca ou Leilão)"""
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcements')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    listing_type = models.CharField('Tipo de Anúncio', max_length=10, choices=ListingType.choices)
    status = models.CharField('Status', max_length=10, choices=ListingStatus.choices, default=ListingStatus.ACTIVE)

    # Venda
    price = models.DecimalField('Preço de Venda', max_digits=10, decimal_places=2, null=True, blank=True)

    # Leilão
    starting_bid = models.DecimalField('Lance Inicial', max_digits=10, decimal_places=2, null=True, blank=True)
    auction_end = models.DateTimeField('Fim do Leilão', null=True, blank=True)

    # Troca
    desired_item_desc = models.TextField('O que aceita em troca', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_auction_active(self):
        if self.listing_type == ListingType.AUCTION and self.auction_end:
            return self.status == ListingStatus.ACTIVE and timezone.now() < self.auction_end
        return False

    def __str__(self):
        return f"{self.get_listing_type_display()} - {self.item.title}"


class Bid(models.Model):
    """Lances de Leilão"""
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='bids')
    bidder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField('Valor do Lance', max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-amount']


class TradeProposal(models.Model):
    """Propostas de Troca"""
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='proposals')
    proposer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    offered_item = models.ForeignKey(Item, on_delete=models.CASCADE)
    message = models.TextField('Mensagem/Proposta', blank=True, null=True)
    is_accepted = models.BooleanField('Aceita', null=True, default=None)
    timestamp = models.DateTimeField(auto_now_add=True)

class Order(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Aguardando Pagamento'),
        ('PAID', 'Pago'),
        ('CANCELLED', 'Cancelado'),
    )
    
    announcement = models.ForeignKey('Announcement', on_delete=models.CASCADE, related_name='orders')
    
    # 👈 2. Use settings.AUTH_USER_MODEL diretamente no ForeignKey:
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='purchases'
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='sales'
    )
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    pix_copy_paste = models.TextField(blank=True, null=True)
    pix_qr_code_base64 = models.TextField(blank=True, null=True)
    gateway_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.announcement.item.title}"