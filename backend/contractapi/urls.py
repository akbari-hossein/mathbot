from django.urls import path

from . import views

# mounted at /api/contract/
urlpatterns = [
    # public / logged in users
    path('config/', views.ContractConfigView.as_view(), name='contract-config'),
    path('contests/<int:contest_id>/', views.ContestOnChainView.as_view(), name='contract-contest'),
    path(
        'contests/<int:contest_id>/participants/<str:wallet>/',
        views.ParticipantStatusView.as_view(),
        name='contract-participant',
    ),
    # admin only
    path('admin/contests/', views.CreateContestView.as_view(), name='contract-create-contest'),
    path('admin/contests/<int:contest_id>/deadline/', views.SignupDeadlineView.as_view(), name='contract-deadline'),
    path('admin/contests/<int:contest_id>/budget/', views.AddBudgetView.as_view(), name='contract-budget'),
    path('admin/contests/<int:contest_id>/cancel/', views.CancelContestView.as_view(), name='contract-cancel'),
    path('admin/contests/<int:contest_id>/refund/', views.RefundView.as_view(), name='contract-refund'),
    path('admin/contests/<int:contest_id>/award/top3/', views.AwardTop3View.as_view(), name='contract-award-top3'),
    path(
        'admin/contests/<int:contest_id>/award/percentage/',
        views.AwardPercentageView.as_view(),
        name='contract-award-percentage',
    ),
    path('admin/contests/<int:contest_id>/award/fixed/', views.AwardFixedView.as_view(), name='contract-award-fixed'),
    path('admin/contests/<int:contest_id>/award/duel/', views.AwardDuelView.as_view(), name='contract-award-duel'),
    path('admin/contests/<int:contest_id>/award/custom/', views.AwardCustomView.as_view(), name='contract-award-custom'),
    path('admin/contests/<int:contest_id>/withdraw/', views.WithdrawView.as_view(), name='contract-withdraw'),
    path('admin/pause/', views.PauseView.as_view(), name='contract-pause'),
    path('admin/unpause/', views.UnpauseView.as_view(), name='contract-unpause'),
    path('admin/owner/', views.OwnerInfoView.as_view(), name='contract-owner'),
    path('admin/transactions/', views.TransactionListView.as_view(), name='contract-transactions'),
    path(
        'admin/transactions/<str:tx_hash>/',
        views.TransactionDetailView.as_view(),
        name='contract-transaction-detail',
    ),
]
