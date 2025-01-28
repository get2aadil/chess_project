# game/routing.py

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/game/(?P<game_id>\w+)/$', consumers.GameConsumer.as_asgi()),
    re_path(r'ws/challenges/$', consumers.ChallengeConsumer.as_asgi()),
    re_path(r'ws/online_users/$', consumers.OnlineUsersConsumer.as_asgi()),
]
