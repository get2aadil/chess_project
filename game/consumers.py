import json
import chess  # Ensure python-chess is installed
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from channels.db import database_sync_to_async
from .models import Game

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'

        # Join game group
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )

        await self.accept()
        print(f'WebSocket connected: {self.game_group_name}')

    async def disconnect(self, close_code):
        # Leave game group
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )
        print(f'WebSocket disconnected: {self.game_group_name}')

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        move = data.get('move')
        user_id = self.scope['user'].id
        print(f'Received move: {move} from user: {user_id} in game: {self.game_id}')

        # Process the move
        result = await self.process_move(user_id, move)

        if result['success']:
            # Broadcast the move to the game group
            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'game_move',
                    'move': move,
                    'user_id': user_id,
                    'game_over': result.get('game_over', False),
                    'result': result.get('result', None),
                }
            )
            print(f'Move broadcasted: {move} in game: {self.game_id}')
        else:
            # Send error back to the user
            await self.send(text_data=json.dumps({
                'success': False,
                'error': result['error']
            }))
            print(f'Move rejected: {move} in game: {self.game_id} - Reason: {result["error"]}')

    # Receive message from game group
    async def game_move(self, event):
        move = event['move']
        user_id = event['user_id']
        game_over = event.get('game_over', False)
        result = event.get('result', None)
        print(f'Received game_move: {move} from user: {user_id} in game: {self.game_id}')

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'success': True,
            'move': move,
            'user_id': user_id,
            'game_over': game_over,
            'result': result,
        }))

    @database_sync_to_async
    def process_move(self, user_id, move):
        try:
            game = Game.objects.get(id=self.game_id, is_active=True)
            board = chess.Board(game.fen_state)

            # Determine if it's the user's turn
            active_color = board.turn  # True for White, False for Black
            user = User.objects.get(id=user_id)
            if (active_color and game.player_white != user) or (not active_color and game.player_black != user):
                print(f'User {user_id} attempted to move out of turn in game {self.game_id}')
                return {'success': False, 'error': "It's not your turn."}

            # Validate move
            move_obj = chess.Move.from_uci(move)
            if move_obj in board.legal_moves:
                board.push(move_obj)
                game.fen_state = board.fen()
                game.move_history = (game.move_history + ',' + move) if game.move_history else move
                game.save()

                # Check if game is over
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
                    print(f'Game {self.game_id} concluded with outcome: {game.outcome}')
                    return {'success': True, 'game_over': True, 'result': game.outcome}
                print(f'Move {move} processed in game {self.game_id}')
                return {'success': True}
            else:
                legal_moves = [m.uci() for m in board.legal_moves]
                print(f'Illegal move attempted: {move} in game {self.game_id}')
                return {'success': False, 'error': f"Illegal move! Possible moves: {', '.join(legal_moves)}"}
        except Game.DoesNotExist:
            print(f'Game {self.game_id} does not exist or is inactive.')
            return {'success': False, 'error': "Game does not exist or is inactive."}
        except ValueError:
            print(f'Invalid move format: {move} in game {self.game_id}')
            return {'success': False, 'error': "Invalid move format."}
        except Exception as e:
            print(f'Unexpected error processing move: {move} in game {self.game_id}')
            return {'success': False, 'error': "An unexpected error occurred."}
        
    async def game_over(self, event):
        result = event.get('result')
        user_id = event.get('user_id')
        print(f'Game over in game {self.game_id} with result: {result}')

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'success': True,
            'game_over': True,
            'result': result,
            'user_id': user_id,
        }))

class ChallengeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            # Reject the connection
            await self.close()
        else:
            # Use the user's ID to create a unique group
            self.group_name = f'user_{self.user.id}'
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            print(f'WebSocket connected for challenges: {self.group_name}')

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            print(f'WebSocket disconnected for challenges: {self.group_name}')
        else:
            print('WebSocket disconnected for challenges: group_name not set')
        
    # Handle incoming messages from the WebSocket
    async def receive(self, text_data):
        # Currently, clients don't send messages to this consumer
        pass

    # Handle challenge notifications
    async def challenge_notification(self, event):
        await self.send(text_data=json.dumps(event['message']))

# game/consumers.py

class OnlineUsersConsumer(AsyncWebsocketConsumer):
    online_users = set()

    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            # Reject the connection
            await self.close()
        else:
            # Add user to the set of online users
            await self.add_online_user(self.user.id)
            await self.accept()
            print(f'WebSocket connected for online users: user_{self.user.id}')

            # Add to the group
            await self.channel_layer.group_add(
                'online_users_group',
                self.channel_name
            )

            # Send the current list of online users to the connected client
            await self.send_online_users_list()

            # Notify other clients about the new online user
            await self.broadcast_online_users()

    async def disconnect(self, close_code):
        if not self.user.is_anonymous:
            # Remove user from the set of online users
            await self.remove_online_user(self.user.id)
            print(f'WebSocket disconnected for online users: user_{self.user.id}')

            # Remove from the group
            await self.channel_layer.group_discard(
                'online_users_group',
                self.channel_name
            )

            # Notify other clients about the user going offline
            await self.broadcast_online_users()

    # Class methods to manage the online users set
    @classmethod
    @database_sync_to_async
    def add_online_user(cls, user_id):
        cls.online_users.add(user_id)

    @classmethod
    @database_sync_to_async
    def remove_online_user(cls, user_id):
        cls.online_users.discard(user_id)

    @classmethod
    @database_sync_to_async
    def get_online_users(cls):
        return list(cls.online_users)

    # Method to send the online users list to the connected client
    async def send_online_users_list(self):
        online_user_ids = await self.get_online_users()
        online_users = await database_sync_to_async(list)(
            User.objects.filter(id__in=online_user_ids).values('id', 'username')
        )
        await self.send(text_data=json.dumps({
            'type': 'online_users',
            'online_users': online_users
        }))

    # Method to broadcast the online users list to all clients
    async def broadcast_online_users(self):
        online_user_ids = await self.get_online_users()
        online_users = await database_sync_to_async(list)(
            User.objects.filter(id__in=online_user_ids).values('id', 'username')
        )
        message = {
            'type': 'online_users',
            'online_users': online_users
        }
        # Broadcast to all connected clients
        await self.channel_layer.group_send(
            'online_users_group',
            {
                'type': 'online_users_message',  # Unique handler name
                'message': message
            }
        )

    # Handler for messages sent to the group
    async def online_users_message(self, event):
        message = event['message']
        # Send message to WebSocket
        await self.send(text_data=json.dumps(message))

    async def receive(self, text_data):
        # No need to handle incoming messages from clients for now
        pass
