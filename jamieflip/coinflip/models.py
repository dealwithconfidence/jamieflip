from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    balance = models.IntegerField(default=100)
    daily_claimed = models.DateTimeField(null=True, blank=True)

class Coinflip(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_flips')
    joiner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='joined_flips')
    creator_choice_is_heads = models.BooleanField()
    wager_amount = models.IntegerField()
    pub_time = models.DateTimeField(auto_now_add=True)
    is_open = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_flips')
    complete_date = models.DateTimeField(null=True, blank=True)