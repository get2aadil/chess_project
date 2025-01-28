from django.db import models
from django.contrib.auth.models import User

class Game(models.Model):
    player_white = models.ForeignKey(User, on_delete=models.CASCADE, related_name='games_as_white')
    player_black = models.ForeignKey(User, on_delete=models.CASCADE, related_name='games_as_black')
    fen_state = models.TextField()  # Store current board state in FEN notation
    is_active = models.BooleanField(default=True)  # Game is active or completed
    move_history = models.TextField(blank=True, null=True)  # UCI move history
    outcome = models.CharField(
        max_length=20,
        choices=[
            ('white_win', 'White Win'),
            ('black_win', 'Black Win'),
            ('draw', 'Draw'),
            ('white_resigned', 'White Resigned'),
            ('black_resigned', 'Black Resigned')
        ],
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

class JournalEntry(models.Model):
    game = models.OneToOneField(Game, on_delete=models.CASCADE)
    entry = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Challenge(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    challenger = models.ForeignKey(User, related_name='challenges_sent', on_delete=models.CASCADE)
    opponent = models.ForeignKey(User, related_name='challenges_received', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    challenger_notified = models.BooleanField(default=False)  
    game = models.ForeignKey('Game', null=True, blank=True, on_delete=models.SET_NULL)
    
    def __str__(self):
        return f"{self.challenger.username} challenged {self.opponent.username} - {self.status}"