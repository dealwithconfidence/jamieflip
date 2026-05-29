from django.shortcuts import render
from django.contrib.auth import login, authenticate
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db import models
from asgiref.sync import async_to_sync
from .models import Coinflip
from channels.layers import get_channel_layer
from django.middleware.csrf import get_token
import random
import json
from django.http import JsonResponse

User = get_user_model()

def signup_view(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            username = body["username"]
            password = body["password"]
            if User.objects.filter(username=username).exists():
                raise Exception("account already exists")
            
            user = User.objects.create_user(username=username, password=password)

            login(request, user)
            return JsonResponse({
                'status' : 'ok',
                'username' : user.username,
                'balance' : user.balance,
                'user_id' : user.id
            })
        except Exception as e:
            return JsonResponse({'error' : str(e)})

def login_view(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            username = body["username"]
            password = body["password"]
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return JsonResponse({
                    'status' : 'ok',
                    'username' : user.username,
                    'balance': user.balance
                })
            else:
                raise Exception("Invalid Credentials")
        except Exception as e:
            return JsonResponse({'error' : str(e)})

def index(request):
    get_token(request)
    if request.user.is_authenticated:
        return render(request, 'coinflip/index.html', {
            'is_authenticated': True,
            'username': request.user.username,
            'balance': request.user.balance,
            'user_id': request.user.id
        })
    return render(request, 'coinflip/index.html', {
        'is_authenticated': False
    })

def get_balance(request):
    if not request.user.is_authenticated:
        return JsonResponse({'login': 'login'})
    return JsonResponse({'balance': request.user.balance})

def view_profile(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            profile_id = int(body['profile_id'])
            user_stats = User.objects.get(id=profile_id)

            wins = Coinflip.objects.filter(winner=user_stats,is_completed=True).count()
            total_flips = Coinflip.objects.filter(is_completed=True).filter(models.Q(creator=user_stats) | models.Q(joiner=user_stats)).count()
            losses = total_flips - wins

            total_won = Coinflip.objects.filter(winner=user_stats, is_completed=True).aggregate(
                total=models.Sum('wager_amount')
            )['total'] or 0
            total_wagered = Coinflip.objects.filter(is_completed=True).filter(models.Q(creator=user_stats) | models.Q(joiner=user_stats)).aggregate(
                total=models.Sum('wager_amount')
            )['total'] or 0
            pnl = (total_won * 2) - total_wagered

            return JsonResponse({
                'username': user_stats.username,
                'total_wins': wins,
                'total_losses': losses,
                'total_flips': total_flips,
                'total_wagered' :total_wagered,
                'pnl': pnl
            })
        except Exception as e:
            return JsonResponse({'error' : str(e)})

def create_coinflip(request):
    if not request.user.is_authenticated:
        return JsonResponse({'login': 'login'})
    if request.method == "POST":
        try:
            with transaction.atomic():
                body = json.loads(request.body)
                wager_amount = int(body['wager_amount'])
                creator_choice_is_heads = body['creator_choice_is_heads']
                user = request.user

                if wager_amount > user.balance:
                    raise Exception("Insufficient Balance")
                if creator_choice_is_heads not in [True, False]:
                    raise Exception("Invalid Submit")
                coinflip = Coinflip.objects.create(
                    creator = user,
                    creator_choice_is_heads = creator_choice_is_heads,
                    wager_amount = wager_amount,
                )


                user.balance -= wager_amount
                user.save()
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                     'coinflips',

                {
                    'type': 'coinflip_update',
                    'action': 'created',
                    'coinflip_id': coinflip.id,
                    'wager_amount': wager_amount,
                    'creator': user.username,
                    'creator_id': user.id,        
                    'creator_choice_is_heads': creator_choice_is_heads
                }
            )
            return JsonResponse({'status':'ok'})
        except Exception as e:
            return JsonResponse({'error':str(e)})

def join_coinflip(request):
    if not request.user.is_authenticated:
        return JsonResponse({'login': 'login'})
    if request.method == "POST":
        try:
            with transaction.atomic():
                body = json.loads(request.body)
                coinflip_id = body['coinflip_id']
                user = request.user
                coinflip = Coinflip.objects.select_for_update().get(id=coinflip_id)
                
                if coinflip.is_open == False:
                    raise Exception("Invalid coinflip")
                if coinflip.wager_amount > user.balance:
                    raise Exception("Insufficient Balance")
                if coinflip.creator == user:
                    raise Exception("cant join own flip")
               
                coinflip.joiner = user
                user.balance -= coinflip.wager_amount
                coinflip.is_open = False
                winning_side = random.choice([True,False])
                if coinflip.creator_choice_is_heads == winning_side:
                    coinflip.winner = coinflip.creator
                    coinflip.creator.balance += coinflip.wager_amount*2
                else:
                    coinflip.winner = coinflip.joiner
                    coinflip.joiner.balance += coinflip.wager_amount*2
                coinflip.is_completed = True
                coinflip.complete_date = timezone.now()

                coinflip.save()
                coinflip.creator.save()
                user.save()

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                     'coinflips',

                {
                    'type': 'coinflip_update',
                    'action': 'joined',
                    'coinflip_id': coinflip.id,
                    'joiner': user.username,
                    'joiner_id': user.id,           
                    'creator': coinflip.creator.username,  
                    'creator_id': coinflip.creator.id,     
                    'winner': coinflip.winner.username,
                    'heads_won': winning_side,
                    'wager_amount': coinflip.wager_amount  
                }
            )
            return JsonResponse({'status':'ok'})
        except Exception as e:
            return JsonResponse({'error' : str(e)})

def daily_claimed_check(request):
    if not request.user.is_authenticated:
        return JsonResponse({'login': 'login'})
    if request.method == "GET":
        user = request.user
        today = timezone.now().date()
        
        if user.daily_claimed is None:
            return JsonResponse({'status': 'available'})
        
        if user.daily_claimed < today:
            return JsonResponse({'status': 'available'})
        
        return JsonResponse({'status': 'unavailable'})

def daily_claim(request):
    if not request.user.is_authenticated:
        return JsonResponse({'login': 'login'})
    if request.method == "POST":
        try:
            user = request.user
            today = timezone.now().date()
            
            if user.daily_claimed is None:
                with transaction.atomic():
                    user.daily_claimed = timezone.now()
                    user.balance +=100
                    user.save()
                    return JsonResponse({'status': 'ok', 'new_balance': user.balance})
                
            if user.daily_claimed.date() < today:
                with transaction.atomic():
                    user.daily_claimed = timezone.now()
                    user.balance +=100
                    user.save()
                    return JsonResponse({'status': 'ok', 'new_balance': user.balance})
        except Exception as e:
            return JsonResponse({'error':str(e)}) 