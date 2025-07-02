from .views import *
from django.urls import path, include

urlpatterns = [
    path('create-comp/', CreateCompView.as_view(), name='create_comp'),
    path('create-comp-free/', CreateCompFreeView.as_view(), name='create_comp_free'),
    path('award-winners/', AwardWinnersView.as_view(), name='award_winners'),
    path('award-with-percentage/', AwardWithPercentageView.as_view(), name='award_with_percentage'),
    path('withdraw-winners/', WithdrawWinnersView.as_view(), name='withdraw_winners'),
    path('comp-total/', CompTotalView.as_view(), name='comp_total'),
    path('comp-status/', CompStatusView.as_view(), name='comp_status'),
    path('comp-exist/', CompExistView.as_view(), name='comp_exist'),
]