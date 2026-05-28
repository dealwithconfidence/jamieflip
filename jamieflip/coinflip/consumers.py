import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from .models import Coinflip

class CoinflipConsumer(WebsocketConsumer):
    def connect(self):
        async_to_sync(self.channel_layer.group_add)(
            'coinflips',
            self.channel_name
        )
        self.accept()
        coinflips = Coinflip.objects.filter(is_open=True).values(
                'id', 'wager_amount', 'creator__username', 'creator__id', 'creator_choice_is_heads'
            )
        self.send(text_data=json.dumps({
            'type': 'initial',
            'coinflips': list(coinflips)
        }))
    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            'coinflips',
            self.channel_name
        )

    def coinflip_update(self, event):
        self.send(text_data=json.dumps(event))
    def receive(self, text_data):
        pass