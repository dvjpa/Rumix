import json
from decimal import Decimal
import mercadopago

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Q

# Importação dos Modelos e Formulários
from .models import Item, Announcement, ListingType, ListingStatus, Bid, Order
from .forms import AnnouncementForm, ItemForm

# Token do Mercado Pago
MERCADO_PAGO_TOKEN = "SEU_TOKEN_DO_MERCADO_PAGO_AQUI"


def marketplace_home(request):
    """
    Página Principal do Comércio.
    Suporta navegação por abas (?tipo=SALE | AUCTION | EXCHANGE | ALL ou ?type=...)
    e busca simples por palavra-chave (?q=termo).
    """
    # Captura o parâmetro das abas (suporta tanto 'tipo' quanto 'type')
    tipo_filtro = request.GET.get('tipo') or request.GET.get('type') or 'ALL'
    busca = request.GET.get('q', '').strip()

    announcements = Announcement.objects.filter(status=ListingStatus.ACTIVE)

    # Filtragem das 4 categorias principais
    if tipo_filtro == 'PRODUCT':
        # Filtra anúncios de venda que pertencem a produtos/insumos
        announcements = announcements.filter(
            listing_type=ListingType.SALE
        ).exclude(item__title__icontains='cabeça').exclude(item__title__icontains='gado')
    elif tipo_filtro == 'SALE' or tipo_filtro == ListingType.SALE:
        # Filtra vendas gerais ou animais
        announcements = announcements.filter(listing_type=ListingType.SALE)
    elif tipo_filtro == 'AUCTION' or tipo_filtro == ListingType.AUCTION:
        announcements = announcements.filter(listing_type=ListingType.AUCTION)
    elif tipo_filtro == 'EXCHANGE' or tipo_filtro == ListingType.EXCHANGE:
        announcements = announcements.filter(listing_type=ListingType.EXCHANGE)

    # Filtro por barra de pesquisa
    if busca:
        announcements = announcements.filter(
            Q(item__title__icontains=busca) | Q(item__description__icontains=busca)
        )

    announcements = announcements.order_by('-created_at')

    return render(request, 'marketplace/home.html', {
        'announcements': announcements,
        'tipo_filtro': tipo_filtro,
        'filter_type': tipo_filtro,
        'busca': busca,
    })

def announcement_detail(request, pk):
    """Exibe os detalhes de um anúncio específico."""
    announcement = get_object_or_404(Announcement, pk=pk)
    return render(request, 'marketplace/detail.html', {'announcement': announcement})


@login_required
def create_announcement(request):
    """Criação de um novo anúncio."""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, user=request.user)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.seller = request.user
            announcement.save()
            messages.success(request, 'Anúncio publicado com sucesso!')
            return redirect('marketplace:home')
    else:
        form = AnnouncementForm(user=request.user)

    return render(request, 'marketplace/create_announcement.html', {'form': form})


@login_required
def item_list(request):
    """Lista todos os itens pertencentes ao usuário logado."""
    user_items = Item.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'marketplace/item_list.html', {'items': user_items})


@login_required
def create_item(request):
    """Cadastra um novo item pertencente ao usuário."""
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            messages.success(request, f'Item "{item.title}" cadastrado com sucesso!')
            
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('marketplace:item_list')
    else:
        form = ItemForm()

    return render(request, 'marketplace/create_item.html', {'form': form})


@login_required
def place_bid(request, pk):
    """Permite que compradores façam lances em leilões ativos."""
    announcement = get_object_or_404(Announcement, pk=pk, listing_type=ListingType.AUCTION)

    # Verifica se o leilão está ativo
    if hasattr(announcement, 'is_auction_active') and not announcement.is_auction_active():
        messages.error(request, "Este leilão já foi encerrado ou não está ativo.")
        return redirect('marketplace:detail', pk=pk)

    # Impede que o próprio vendedor dê lances
    if announcement.seller == request.user:
        messages.error(request, "Você não pode dar lances no seu próprio leilão.")
        return redirect('marketplace:detail', pk=pk)

    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
        except (ValueError, TypeError):
            messages.error(request, "Valor de lance inválido.")
            return redirect('marketplace:detail', pk=pk)

        highest = announcement.highest_bid
        min_required = highest.amount if highest else (announcement.starting_bid or Decimal('0'))

        if amount <= min_required:
            messages.error(request, f"O seu lance deve ser maior do que R$ {min_required:.2f}.")
            return redirect('marketplace:detail', pk=pk)

        # Salva o lance efetuado
        Bid.objects.create(
            announcement=announcement,
            bidder=request.user,
            amount=amount
        )
        messages.success(request, f"Lance de R$ {amount:.2f} efetuado com sucesso!")

    return redirect('marketplace:detail', pk=pk)


@login_required
def checkout_pix(request, pk):
    """Gera a cobrança PIX via Mercado Pago para compras de Venda Direta."""
    announcement = get_object_or_404(Announcement, pk=pk, status=ListingStatus.ACTIVE)

    if announcement.seller == request.user:
        messages.error(request, "Você não pode comprar seu próprio item.")
        return redirect('marketplace:detail', pk=pk)

    order, created = Order.objects.get_or_create(
        announcement=announcement,
        buyer=request.user,
        seller=announcement.seller,
        defaults={
            'amount': announcement.price or Decimal('0.0'),
            'status': 'PENDING'
        }
    )

    if not order.pix_copy_paste:
        try:
            sdk = mercadopago.SDK(MERCADO_PAGO_TOKEN)

            payment_data = {
                "transaction_amount": float(order.amount),
                "description": f"Compra Rumix - {announcement.item.title}",
                "payment_method_id": "pix",
                "payer": {
                    "email": request.user.email or f"{request.user.username}@rumix.com",
                    "first_name": request.user.first_name or request.user.username,
                    "last_name": request.user.last_name or "Usuario",
                }
            }

            payment_response = sdk.payment().create(payment_data)
            payment = payment_response.get("response", {})

            if "point_of_interaction" in payment:
                tx_data = payment["point_of_interaction"]["transaction_data"]
                order.pix_copy_paste = tx_data["qr_code"]
                order.pix_qr_code_base64 = tx_data["qr_code_base64"]
                order.gateway_id = str(payment.get("id"))
                order.save()
            else:
                messages.error(request, "Falha ao gerar QR Code do PIX com o gateway.")
        except Exception as e:
            messages.error(request, f"Erro na integração do pagamento: {str(e)}")

    return render(request, 'marketplace/payment_pix.html', {
        'order': order,
        'announcement': announcement
    })


@login_required
def pay_auction_winner(request, pk):
    """Gera cobrança PIX para o vencedor de um leilão encerrado."""
    announcement = get_object_or_404(Announcement, pk=pk, listing_type=ListingType.AUCTION)

    highest_bid = announcement.highest_bid

    # Validações: O leilão precisa estar encerrado e o usuário precisa ser o maior lançador
    if hasattr(announcement, 'is_auction_active') and announcement.is_auction_active():
        messages.error(request, "O leilão ainda está em andamento.")
        return redirect('marketplace:detail', pk=pk)

    if not highest_bid or highest_bid.bidder != request.user:
        messages.error(request, "Apenas o vencedor do leilão pode realizar o pagamento.")
        return redirect('marketplace:detail', pk=pk)

    # Marca o anúncio como concluído ao iniciar o checkout
    if announcement.status == ListingStatus.ACTIVE:
        announcement.status = ListingStatus.COMPLETED
        announcement.save()

    sdk = mercadopago.SDK(MERCADO_PAGO_TOKEN)

    payment_data = {
        "transaction_amount": float(highest_bid.amount),
        "description": f"Leilão Vencido: {announcement.item.title}",
        "payment_method_id": "pix",
        "payer": {
            "email": request.user.email or f"{request.user.username}@rumix.com",
            "first_name": request.user.first_name or request.user.username,
        }
    }

    payment_response = sdk.payment().create(payment_data)
    payment = payment_response.get("response", {})

    qr_code_base64 = payment.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code_base64")
    qr_code_copy_paste = payment.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")
    gateway_id = str(payment.get("id", ""))

    order, created = Order.objects.get_or_create(
        announcement=announcement,
        buyer=request.user,
        defaults={
            'seller': announcement.seller,
            'amount': highest_bid.amount,
            'pix_qr_code_base64': qr_code_base64,
            'pix_copy_paste': qr_code_copy_paste,
            'gateway_id': gateway_id,
            'status': 'PENDING'
        }
    )

    if not created:
        order.amount = highest_bid.amount
        order.pix_qr_code_base64 = qr_code_base64
        order.pix_copy_paste = qr_code_copy_paste
        order.gateway_id = gateway_id
        order.save()

    return render(request, 'marketplace/payment_pix.html', {
        'announcement': announcement,
        'order': order
    })


@csrf_exempt
@require_POST
def mercadopago_webhook(request):
    """Webhook do Mercado Pago para confirmação automática de pagamento."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    action_type = data.get('type') or data.get('action')
    payment_id = None

    if action_type in ['payment', 'payment.updated', 'payment.created']:
        payment_data = data.get('data', {})
        payment_id = payment_data.get('id')
    elif 'id' in data and data.get('entity') == 'payment':
        payment_id = data.get('id')

    if payment_id:
        sdk = mercadopago.SDK(MERCADO_PAGO_TOKEN)
        payment_info = sdk.payment().get(str(payment_id))
        payment_response = payment_info.get("response", {})

        status = payment_response.get("status")

        if status == "approved":
            order = Order.objects.filter(gateway_id=str(payment_id)).first()

            if order and order.status != 'PAID':
                order.status = 'PAID'
                order.save()

                # Marca o anúncio como concluído
                announcement = order.announcement
                announcement.status = ListingStatus.COMPLETED
                announcement.save()

                return JsonResponse({'status': 'order_updated_to_paid'}, status=200)

    return HttpResponse(status=200)