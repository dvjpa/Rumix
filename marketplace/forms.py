from django import forms
from .models import Announcement, Item, ListingType

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Trator Massey Ferguson 275 / Vaca Girolando'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descreva detalhadamente o item, estado de conservação, especificações, etc.'
            }),
        }

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['item', 'listing_type', 'price', 'starting_bid', 'auction_end', 'desired_item_desc']
        
        widgets = {
            'item': forms.Select(attrs={
                'class': 'form-select',
            }),
            'listing_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_listing_type'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
            }),
            'starting_bid': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
            }),
            'auction_end': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',  # Ativa o seletor nativo de data e hora do navegador
            }),
            'desired_item_desc': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descreva o que você gostaria de receber em troca...',
            }),
        }

    def __init__(self, *args, **kwargs):
        # Permite filtrar itens pertencentes apenas ao usuário logado se o 'user' for passado
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['item'].queryset = self.fields['item'].queryset.filter(owner=user)

    def clean(self):
        cleaned_data = super().clean()
        listing_type = cleaned_data.get('listing_type')

        if listing_type == ListingType.SALE:
            if not cleaned_data.get('price'):
                self.add_error('price', 'Para vendas, informe o preço.')
        elif listing_type == ListingType.AUCTION:
            if not cleaned_data.get('starting_bid'):
                self.add_error('starting_bid', 'Informe o valor inicial do leilão.')
            if not cleaned_data.get('auction_end'):
                self.add_error('auction_end', 'Informe a data e hora de encerramento.')
        elif listing_type == ListingType.EXCHANGE:
            if not cleaned_data.get('desired_item_desc'):
                self.add_error('desired_item_desc', 'Informe o que você deseja em troca.')

        return cleaned_data