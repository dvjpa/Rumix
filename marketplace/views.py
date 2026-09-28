from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import mercadopago
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Importações dos Modelos (Incluindo Item e Order)
from .models import Item, Announcement, ListingType, Bid, Order
from .forms import AnnouncementForm, ItemForm

# Defina sua chave/token do Mercado Pago (ou use através do settings.MERCADO_PAGO_TOKEN)
MERCADO_PAGO_TOKEN = "TEST-SEU_ACCESS_TOKEN_AQUI"


def marketplace_home(request):
    filter_type = request.GET.get('type')
    announcements = Announcement.objects.filter(status='ACTIVE')
    
    if filter_type in [ListingType.SALE, ListingType.EXCHANGE, ListingType.AUCTION]:
        announcements = announcements.filter(listing_type=filter_type)

    return render(request, 'marketplace/home.html', {
        'announcements': announcements,
        'filter_type': filter_type,
    })


def announcement_detail(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    return render(request, 'marketplace/detail.html', {'announcement': announcement})


@login_required
def create_announcement(request):
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
def place_bid(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk, listing_type=ListingType.AUCTION)
    
    if hasattr(announcement, 'is_auction_active') and not announcement.is_auction_active():
        messages.error(request, 'Este leilão já foi encerrado.')
        return redirect('marketplace:detail', pk=pk)

    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount', 0))
        except (ValueError, TypeError):
            amount = 0.0

        highest_bid = announcement.bids.order_by('-amount').first()
        min_amount = float(highest_bid.amount) if highest_bid else float(announcement.starting_bid or 0)

        if amount > min_amount:
            Bid.objects.create(announcement=announcement, bidder=request.user, amount=amount)
            messages.success(request, 'Lance realizado com sucesso!')
        else:
            messages.error(request, f'O lance deve ser maior do que R$ {min_amount:.2f}')

    return redirect('marketplace:detail', pk=pk)


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
def checkout_pix(request, pk):
    """Gera cobrança PIX para venda direta e salva no modelo Order."""
    announcement = get_object_or_404(Announcement, pk=pk, status='ACTIVE')

    if announcement.seller == request.user:
        messages.error(request, "Você não pode comprar seu próprio item.")
        return redirect('marketplace:detail', pk=pk)

    order, created = Order.objects.get_or_create(
        announcement=announcement,
        buyer=request.user,
        seller=announcement.seller,
        status='PENDING',
        defaults={'amount': announcement.price or 0.0}
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

@csrf_exempt
@require_POST
def mercadopago_webhook(request):
    """Webhook do Mercado Pago para atualização automática do status do pagamento."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    # O Mercado Pago envia 'type' ou 'action' indicando o evento de 'payment'
    action_type = data.get('type') or data.get('action')
    payment_id = None

    if action_type in ['payment', 'payment.updated', 'payment.created']:
        # O ID do pagamento pode vir em 'data.id'
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
            # Busca o pedido registrado com o gateway_id
            order = Order.objects.filter(gateway_id=str(payment_id)).first()

            if order and order.status != 'PAID':
                # Atualiza o status do Pedido para Pago
                order.status = 'PAID'
                order.save()

                # Marca o anúncio como vendido/concluído
                announcement = order.announcement
                announcement.status = 'COMPLETED'
                announcement.save()

                return JsonResponse({'status': 'order_updated_to_paid'}, status=200)

    return HttpResponse(status=200)