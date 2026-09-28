import json
from channels.generic.websocket import AsyncWebsocketConsumer

class AuctionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.auction_id = self.scope['url_route']['kwargs']['pk']
        self.room_group_name = f'auction_{self.auction_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Lógica para registrar o lance no BD e emitir para todos na sala
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'auction_bid',
                'amount': data['amount'],
                'bidder': data['bidder']
            }
        )

    async def auction_bid(self, event):
        await self.send(text_data=json.dumps(event))