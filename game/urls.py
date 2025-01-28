from django.urls import path
from . import views

urlpatterns = [
    path('new/', views.new_game_view, name='new_game'),
    path('<int:game_id>/', views.game_view, name='game_view'),
    path('play/', views.play_game_view, name='play_game'),
    path('resign/<int:game_id>/', views.resign_game_view, name='resign_game'),
    path('challenge/<int:user_id>/', views.challenge_user_view, name='challenge_user'),
    path('edit_journal/<int:game_id>/', views.edit_journal_view, name='edit_journal'),
    path('delete_game/<int:game_id>/', views.delete_game_view, name='delete_game'),
    path('view_journal/<int:game_id>/', views.view_journal_view, name='view_journal'),
    path('<int:game_id>/move/', views.make_move_view, name='make_move'),

    path('poll_challenges/', views.poll_challenges_view, name='poll_challenges'),
    path('accept_challenge/<int:challenge_id>/', views.accept_challenge_view, name='accept_challenge'),
    path('reject_challenge/<int:challenge_id>/', views.reject_challenge_view, name='reject_challenge'),
    path('poll_challenge_responses/', views.poll_challenge_responses_view, name='poll_challenge_responses'),
    path('get_available_users/', views.get_available_users_view, name='get_available_users'),
]
