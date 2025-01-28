from .models import Game
from django.db.models import Q

def active_game(request):
    if request.user.is_authenticated:
        active_game = Game.objects.filter(
            Q(player_white=request.user) | Q(player_black=request.user),
            is_active=True
        ).first()
        return {
            'is_in_active_game': active_game is not None,
            'active_game_id': active_game.id if active_game else None
        }
    return {
        'is_in_active_game': False,
        'active_game_id': None
    }
