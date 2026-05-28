from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('create/', views.create_coinflip, name='create_coinflip'),
    path('join/', views.join_coinflip, name='join_coinflip'),
    path('dailyclaim/', views.daily_claim, name='daily_claim'),
    path('daily/', views.daily_claimed_check, name='daily_claimed_check'),
    path('balance/', views.get_balance, name='get_balance'),
    path('profile/', views.view_profile, name='view_profile')
]