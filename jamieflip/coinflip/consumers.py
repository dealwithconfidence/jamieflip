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
        coinflips = Coinflip.objects.filter(is_open=True)
        self.send(text_data=json.dumps({
            'type': 'initial',
            'coinflips': list(coinflips.values())
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