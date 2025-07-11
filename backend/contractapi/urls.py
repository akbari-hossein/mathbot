from .views import *
from django.urls import path, include

urlpatterns = [
    path('create-comp/', CreateCompView.as_view(), name ='create_comp'),
    path('create-comp-free/', CreateCompFreeView.as_view(), name ='create_comp_free'),
    path('award-winners/', AwardWinnersView.as_view(), name ='award_winners'),
    path('award-with-percentage/', AwardWithPercentageView.as_view(), name ='award_with_percentage'),
    path('withdraw-winners/', WithdrawWinnersView.as_view(), name ='withdraw_winners'),
    path('comp-total/', CompTotalView.as_view(), name ='comp_total'),
    path('comp-status/', CompStatusView.as_view(), name ='comp_status'),
    path('comp-exist/', CompExistView.as_view(), name ='comp_exist'),
    path('create-tx-metamask/', CreateTxView.as_view(), name = 'create_tx'),
    path('award-for-duel-comp/' , Awardforduel_comp.as_view() , name = 'Duel Awards'),
    path('Award-for-free-comp/' , Awardforfree_comp.as_view() , name = 'award_free_comp'),
    path('Award-for-arbitrary-comp/' , Awardforarbitrary_comp.as_view() , name = 'Competitions_with_desired_prizes_and_desired_winners')
]