import json
import re
from django.shortcuts import render, redirect
from .models import Challenge, Game
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import models  # Add this for models.Q
from django.shortcuts import get_object_or_404
from .models import JournalEntry
import chess
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@login_required
def game_view(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    board_rows = fen_to_dict(game.fen_state)

    # Get active color from FEN
    active_color = game.fen_state.split()[1]  # 'w' or 'b'
    is_your_turn = (active_color == 'w' and request.user == game.player_white) or \
                   (active_color == 'b' and request.user == game.player_black)

    # Prepare game data for JSON
    game_data = {
        'id': game.id,
        'player_white_id': game.player_white.id,
        'player_black_id': game.player_black.id,
        'fen_state': game.fen_state,
        'is_active': game.is_active,
        'move_history': game.move_history.split(',') if game.move_history else [],
        'outcome': game.outcome,
        'created_at': game.created_at.isoformat(),
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        new_board_html = render_to_string('game/partials/board_state.html', {'board_rows': board_rows}, request=request)
        move_history_html = render_to_string('game/partials/move_history.html', {
            'move_history': game.move_history.split(',') if game.move_history else [],
            'game': game
        }, request=request)

        response_data = {
            'success': True,
            'newBoardHTML': new_board_html,
            'moveHistoryHTML': move_history_html,
            'is_your_turn': is_your_turn,
            'game_data': game_data
        }

        # Include game_over status
        if not game.is_active:
            response_data['game_over'] = True
            response_data['result'] = game.outcome

        return JsonResponse(response_data)

    # If not an AJAX request, return normal template rendering
    return render(request, 'game/play_game.html', {
        'game': game,
        'board_rows': board_rows,
        'move_history': game.move_history.split(',') if game.move_history else [],
        'game_data_json': json.dumps(game_data, cls=DjangoJSONEncoder),
        'opponent': game.player_black if request.user == game.player_white else game.player_white,
        'is_your_turn': is_your_turn
    })

@login_required
def resign_game_view(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    # Check if the user is one of the players and the game is active
    if request.user not in [game.player_white, game.player_black]:
        error_message = 'You are not a participant of this game.'
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_message}, status=403)
        else:
            messages.error(request, error_message)
            return redirect('play_game')
    
    if not game.is_active:
        error_message = 'The game is already concluded.'
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_message}, status=400)
        else:
            messages.error(request, error_message)
            return redirect('play_game')
    
    # Determine who resigned and set the outcome accordingly
    if request.user == game.player_white:
        game.outcome = 'white_resigned'
    else:
        game.outcome = 'black_resigned'
    game.is_active = False
    game.save()
    
    # Send a message to the WebSocket group
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'game_{game_id}',
        {
            'type': 'game_over',   # Custom message type
            'result': game.outcome,
            'user_id': request.user.id,
        }
    )

    # Add a message to the user
    success_message = 'You have resigned from the game.'
    messages.success(request, success_message)
    
    # Determine the type of response based on the request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': success_message})
    else:
        return redirect('play_game')  # Redirect to home or any other appropriate page

@login_required
def challenge_user_view(request, user_id):
    opponent = get_object_or_404(User, id=user_id)

    # Check if the opponent is online
    online_users = get_online_users()
    if opponent not in online_users:
        error_msg = f"{opponent.username} is currently offline and cannot be challenged."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        else:
            messages.error(request, error_msg)
            return redirect('new_game')

    # Check if there's already a pending challenge
    existing_challenge = Challenge.objects.filter(
        challenger=request.user,
        opponent=opponent,
        status='pending'
    ).first()

    if existing_challenge:
        warning_msg = f"You have already challenged {opponent.username}. Awaiting their response."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': warning_msg})
        else:
            messages.warning(request, warning_msg)
            return redirect('new_game')

    if request.method == 'POST':
        # Create a new challenge
        challenge = Challenge.objects.create(
            challenger=request.user,
            opponent=opponent,
            status='pending'
        )

        # Send a WebSocket message to the opponent
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{opponent.id}',
            {
                'type': 'challenge_notification',
                'message': {
                    'type': 'new_challenge',
                    'challenger_username': request.user.username,
                    'challenge_id': challenge.id,
                    'timestamp': challenge.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                }
            }
        )
        
        success_msg = f"You have challenged {opponent.username} to a game!"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'opponent_username': opponent.username})
        else:
            messages.success(request, success_msg)
            return redirect('new_game')

    # If not POST, return an error
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    else:
        return redirect('new_game')

@login_required
def new_game_view(request):
    if request.method == "POST":
        opponent_id = request.POST.get('opponent_id')
        opponent = get_object_or_404(User, id=opponent_id)
        
        # Check if there's already a pending challenge
        existing_challenge = Challenge.objects.filter(
            challenger=request.user, 
            opponent=opponent, 
            status='pending'
        ).first()
        
        if existing_challenge:
            messages.warning(request, f"You have already challenged {opponent.username}. Awaiting their response.")
            return redirect('new_game')
        
        # Create a new challenge
        challenge = Challenge.objects.create(
            challenger=request.user,
            opponent=opponent
        )
        messages.success(request, f"You have challenged {opponent.username} to a game!")
        return redirect('new_game')  # Redirect back to the new_game page to see the challenge in history
    
    # For GET request, display the list of online users to challenge
    online_users = get_online_users()
    available_users = online_users.exclude(id=request.user.id)
    # Exclude users who already have a pending challenge from the current user
    available_users = available_users.exclude(
        models.Q(challenges_received__challenger=request.user, challenges_received__status='pending') |
        models.Q(challenges_sent__opponent=request.user, challenges_sent__status='pending')
    ).distinct()
    
    # Fetch game history where the user is a player
    game_history = Game.objects.filter(
        models.Q(player_white=request.user) | models.Q(player_black=request.user)
    ).select_related('player_white', 'player_black').order_by('-created_at')
    
    context = {
        'available_users': available_users,
        'game_history': game_history
    }
    return render(request, 'game/new_game.html', context)

@login_required
def play_game_view(request):
    # Check if the user has an active game
    active_game = Game.objects.filter(
        models.Q(player_white=request.user) | models.Q(player_black=request.user),
        is_active=True
    ).first()

    if active_game:
        # Redirect to the current game if there's an active one
        return redirect('game_view', game_id=active_game.id)
    else:
        # If no active game, redirect to the new game page
        return redirect('new_game')
    
# Helper Python code for mapping from an FEN chessboard representation string, to a python dictionary formatted for rendering in a Django template, similar to Sudoku.
def fen_to_dict(fen_string):
    # Mapping of pieces to HTML entities
    piece_to_html = {
        'K': '&#9812;',  # White King
        'Q': '&#9813;',  # White Queen
        'R': '&#9814;',  # White Rook
        'B': '&#9815;',  # White Bishop
        'N': '&#9816;',  # White Knight
        'P': '&#9817;',  # White Pawn
        'k': '&#9818;',  # Black King
        'q': '&#9819;',  # Black Queen
        'r': '&#9820;',  # Black Rook
        'b': '&#9821;',  # Black Bishop
        'n': '&#9822;',  # Black Knight
        'p': '&#9823;',  # Black Pawn
    }

    # Get the position part of the FEN string
    position_part = fen_string.split(' ')[0]
    ranks = position_part.split('/')

    rows_list = []

    for rank_index, rank_str in enumerate(ranks):
        rank_number = 8 - rank_index  # Rank numbers from 8 to 1
        rank_dict = {}
        file_index = 0  # Files from 'a' to 'h'
        for c in rank_str:
            if c.isdigit():
                n = int(c)
                for _ in range(n):
                    if file_index >= 8:
                        break  # Safety check
                    file_letter = chr(ord('a') + file_index)
                    position = f"{file_letter}{rank_number}"
                    rank_dict[position] = '&nbsp;'
                    file_index += 1
            else:
                if file_index >= 8:
                    break  # Safety check
                file_letter = chr(ord('a') + file_index)
                position = f"{file_letter}{rank_number}"
                rank_dict[position] = piece_to_html.get(c, '&nbsp;')
                file_index += 1
        rows_list.append(rank_dict)

    return rows_list

@login_required
def edit_journal_view(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    # Check if the user is one of the players
    if request.user not in [game.player_white, game.player_black]:
        return render(request, '403.html')  # Forbidden access

    # Allow editing only if the game is completed
    if game.is_active:
        messages.error(request, "Cannot edit journal for an active game.")
        return redirect('play_game')

    journal_entry, created = JournalEntry.objects.get_or_create(game=game)

    if request.method == "POST":
        journal_entry.entry = request.POST.get('journal_entry')
        journal_entry.save()
        messages.success(request, "Journal entry saved successfully.")
        return redirect('play_game')  # Redirect to home after saving

    # Determine the opponent's username
    if request.user == game.player_white:
        opponent = game.player_black
    else:
        opponent = game.player_white

    context = {
        'game': game,
        'journal_entry': journal_entry,
        'opponent': opponent
    }
    return render(request, 'game/edit_journal.html', context)

@login_required
def delete_game_view(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    # Check if the user is one of the players
    if request.user in [game.player_white, game.player_black]:
        # Delete associated journal entry if it exists
        game.delete()
        messages.success(request, "Game and associated journal entry deleted successfully.")
    else:
        messages.error(request, "You do not have permission to delete this game.")

    return redirect('play_game')

@login_required
def make_move_view(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    board = chess.Board(game.fen_state)

    if request.method == "POST":
        # Determine whose turn it is
        active_color = game.fen_state.split()[1]  # 'w' or 'b'
        is_user_white = request.user == game.player_white
        is_user_black = request.user == game.player_black
        if (active_color == 'w' and not is_user_white) or (active_color == 'b' and not is_user_black):
            return JsonResponse({"success": False, "error": "It's not your turn."})

        move_input = json.loads(request.body).get("move")

        # Validate move format using regex (including promotions)
        if not re.match(r"^[a-h][1-8][a-h][1-8][qrbnQBRN]?$", move_input):
            return JsonResponse({"success": False, "error": "Invalid move format! Please use e2e4 or e7e8q for promotions."})

        try:
            move = chess.Move.from_uci(move_input)
            if move in board.legal_moves:
                board.push(move)
                game.fen_state = board.fen()
                game.move_history = (game.move_history + ',' + move_input) if game.move_history else move_input
                game.save()

                # Render updated chessboard and move history
                new_board_html = render_to_string('game/partials/board_state.html', {
                    'board_rows': fen_to_dict(game.fen_state)
                }, request=request)  # Include request here
                move_history_html = render_to_string('game/partials/move_history.html', {
                    'move_history': game.move_history.split(',') if game.move_history else [],
                    'game': game
                }, request=request)  # Include request here

                response_data = {
                    "success": True,
                    "newBoardHTML": new_board_html,
                    "moveHistoryHTML": move_history_html
                }

                # Check if the game is over
                if board.is_game_over():
                    game.is_active = False
                    outcome = board.result()  # '1-0', '0-1', '1/2-1/2'
                    if outcome == '1-0':
                        game.outcome = 'white_win'
                    elif outcome == '0-1':
                        game.outcome = 'black_win'
                    elif outcome == '1/2-1/2':
                        game.outcome = 'draw'
                    else:
                        game.outcome = 'unknown'
                    game.save()
                    response_data["game_over"] = True
                    response_data["result"] = game.outcome

                return JsonResponse(response_data)
            else:
                # Provide a list of legal moves
                legal_moves = ', '.join([board.san(m) for m in board.legal_moves])
                return JsonResponse({
                    "success": False,
                    "error": f"Illegal move! Possible moves: {legal_moves}"
                })
        except ValueError as e:
            return JsonResponse({"success": False, "error": f"Invalid move input! Error: {str(e)}"})

    return JsonResponse({"success": False, "error": "Invalid request!"})

@login_required
def view_journal_view(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    journal_entry = JournalEntry.objects.filter(game=game).first()
    
    # Check if the user is one of the players
    if request.user not in [game.player_white, game.player_black]:
        return render(request, '403.html')  # Forbidden access
    
    # Determine the opponent's username
    if request.user == game.player_white:
        opponent = game.player_black
    else:
        opponent = game.player_white
    
    context = {
        'game': game,
        'journal_entry': journal_entry,
        'opponent': opponent
    }
    return render(request, 'game/view_journal.html', context)

@login_required
def poll_challenges_view(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Get all pending challenges for the logged-in user
        pending_challenges = Challenge.objects.filter(opponent=request.user, status='pending')
        challenges_data = []
        for challenge in pending_challenges:
            challenges_data.append({
                'id': challenge.id,
                'challenger_username': challenge.challenger.username,
                'timestamp': challenge.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            })
        return JsonResponse({'challenges': challenges_data})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def accept_challenge_view(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id, opponent=request.user, status='pending')
    
    if request.method == "POST":
        # Update challenge status
        challenge.status = 'accepted'
        challenge.challenger_notified = False
        challenge.save()
        
        # Create a new game
        game = Game.objects.create(
            player_white=challenge.challenger, 
            player_black=challenge.opponent, 
            fen_state="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            is_active=True
        )

        # Link the game to the challenge
        challenge.game = game
        challenge.save()

        # Send a WebSocket message to the challenger
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{challenge.challenger.id}',
            {
                'type': 'challenge_notification',
                'message': {
                    'type': 'challenge_response',
                    'status': 'accepted',
                    'opponent_username': request.user.username,
                    'game_id': game.id,
                    'timestamp': challenge.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                }
            }
        )

        messages.success(request, f"You have accepted the challenge from {challenge.challenger.username}!")
        return JsonResponse({'success': True, 'game_id': game.id})
    
    return JsonResponse({'success': False}, status=400)

@login_required
def reject_challenge_view(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id, opponent=request.user, status='pending')
    
    if request.method == "POST":
        # Update challenge status
        challenge.status = 'rejected'
        challenge.challenger_notified = False 
        challenge.save()

        # Send a WebSocket message to the challenger
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{challenge.challenger.id}',
            {
                'type': 'challenge_notification',
                'message': {
                    'type': 'challenge_response',
                    'status': 'rejected',
                    'opponent_username': request.user.username,
                    'timestamp': challenge.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                }
            }
        )

        # Notify challenger via messages
        messages.info(request, f"{request.user.username} has rejected your challenge.")
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=400)

@login_required
def poll_challenge_responses_view(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        challenges = Challenge.objects.filter(
            challenger=request.user,
            status__in=['accepted', 'rejected'],
            challenger_notified=False
        )
        challenges_data = []
        for challenge in challenges:
            challenge_data = {
                'id': challenge.id,
                'opponent_username': challenge.opponent.username,
                'status': challenge.status,
                'timestamp': challenge.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            }
            if challenge.status == 'accepted' and challenge.game:
                challenge_data['game_id'] = challenge.game.id
            challenges_data.append(challenge_data)
            # Mark as notified
            challenge.challenger_notified = True
            challenge.save()
        return JsonResponse({'challenges': challenges_data})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def get_available_users_view(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Fetch online users
        online_users = get_online_users()
        available_users = online_users.exclude(id=request.user.id)
        # Exclude users who already have a pending challenge from the current user
        available_users = available_users.exclude(
            models.Q(challenges_received__challenger=request.user, challenges_received__status='pending') |
            models.Q(challenges_sent__opponent=request.user, challenges_sent__status='pending')
        ).distinct()
        users_data = []
        for user in available_users:
            users_data.append({
                'id': user.id,
                'username': user.username,
            })
        return JsonResponse({'available_users': users_data})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
def get_online_users():
    # Get all non-expired sessions
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    
    user_ids = []
    for session in sessions:
        data = session.get_decoded()
        if data.get('_auth_user_id'):
            user_ids.append(data['_auth_user_id'])
    
    # Remove duplicate user IDs
    user_ids = list(set(user_ids))
    
    # Retrieve User objects corresponding to the user IDs
    online_users = User.objects.filter(id__in=user_ids)
    
    return online_users