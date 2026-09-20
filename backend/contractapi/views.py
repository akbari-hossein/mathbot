from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from . import services
from .client import checksum
from .errors import CONTRACT_ERROR_MESSAGES, BlockchainError
from .models import ContractTransaction
from .serializers import (
    BudgetSerializer,
    ContractTransactionSerializer,
    CreateContestSerializer,
    CustomAwardSerializer,
    DeadlineSerializer,
    DuelAwardSerializer,
    FixedAwardSerializer,
    PercentageAwardSerializer,
    RefundSerializer,
    Top3Serializer,
    WithdrawSerializer,
)


class BlockchainAPIView(APIView):
    """Returns blockchain errors as {"error": <code>, "detail": <Persian message>} with a proper status."""

    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def handle_exception(self, exc):
        if isinstance(exc, BlockchainError):
            return Response(exc.as_dict(), status=exc.http_status)
        return super().handle_exception(exc)


# ----------------------------------------------------------------------
# public / user endpoints
# ----------------------------------------------------------------------

class ContractConfigView(BlockchainAPIView):
    """Chain id + contract address for the frontend."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(services.contract_config())


class ContestOnChainView(BlockchainAPIView):
    """On-chain state of a contest (price, balance, participants, deadline, state)."""

    permission_classes = [AllowAny]

    def get(self, request, contest_id):
        contest = services.get_contest(contest_id)
        if contest is None:
            return Response(
                {'error': 'ContestNotFound', 'detail': CONTRACT_ERROR_MESSAGES['ContestNotFound']},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(contest)


class ParticipantStatusView(BlockchainAPIView):
    """Has this wallet paid the signup of the contest, and was it for the logged in user?"""

    permission_classes = [IsAuthenticated]

    def get(self, request, contest_id, wallet):
        wallet = checksum(wallet)
        ref = services.get_participant_ref(contest_id, wallet)
        return Response(
            {
                'contest_id': contest_id,
                'wallet': wallet,
                'registered': ref != 0,
                'is_current_user': ref == request.user.id,
            }
        )


# ----------------------------------------------------------------------
# admin endpoints (the backend wallet signs the transactions)
# ----------------------------------------------------------------------

class OwnerActionView(BlockchainAPIView):
    """Validates the body with `serializer_class`, sends the transaction and returns it (202 = sent, not mined yet).
    Poll GET /api/contract/admin/transactions/<tx_hash>/ until status is success / failed."""

    permission_classes = [IsAdminUser]
    serializer_class = None

    def get_serializer(self, *args, **kwargs):  # used by drf-yasg for the request body
        return self.serializer_class(*args, **kwargs) if self.serializer_class else None

    def perform(self, data, contest_id, user):
        raise NotImplementedError

    @swagger_auto_schema(
        responses={
            202: ContractTransactionSerializer,
            400: 'ورودی نامعتبر یا رد شدن توسط قرارداد: {"error": "<ErrorName>", "detail": "..."}',
            403: 'فقط ادمین',
            502: 'خطای شبکه بلاکچین',
            503: 'تنظیمات بلاکچین ناقص است',
        }
    )
    def post(self, request, contest_id=None):
        data = {}
        if self.serializer_class is not None:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
        tx = self.perform(data, contest_id, request.user)
        return Response(ContractTransactionSerializer(tx).data, status=status.HTTP_202_ACCEPTED)


class CreateContestView(OwnerActionView):
    serializer_class = CreateContestSerializer

    def perform(self, data, contest_id, user):
        return services.create_contest(
            data['contest_id'], data['price_eth'], data['signup_deadline'], data['budget_eth'], user=user
        )


class SignupDeadlineView(OwnerActionView):
    serializer_class = DeadlineSerializer

    def perform(self, data, contest_id, user):
        return services.set_signup_deadline(contest_id, data['signup_deadline'], user=user)


class AddBudgetView(OwnerActionView):
    serializer_class = BudgetSerializer

    def perform(self, data, contest_id, user):
        return services.add_budget(contest_id, data['amount_eth'], user=user)


class CancelContestView(OwnerActionView):
    def perform(self, data, contest_id, user):
        return services.cancel_contest(contest_id, user=user)


class RefundView(OwnerActionView):
    serializer_class = RefundSerializer

    def perform(self, data, contest_id, user):
        return services.refund_participants(contest_id, data['wallets'], user=user)


class AwardTop3View(OwnerActionView):
    serializer_class = Top3Serializer

    def perform(self, data, contest_id, user):
        return services.award_top3(contest_id, data['first'], data['second'], data['third'], user=user)


class AwardPercentageView(OwnerActionView):
    serializer_class = PercentageAwardSerializer

    def perform(self, data, contest_id, user):
        return services.award_with_percentage(
            contest_id, data['first'], data['second'], data['third'], data['percents'], user=user
        )


class AwardFixedView(OwnerActionView):
    serializer_class = FixedAwardSerializer

    def perform(self, data, contest_id, user):
        return services.award_fixed(
            contest_id, data['first'], data['second'], data['third'], data['amounts_eth'], user=user
        )


class AwardDuelView(OwnerActionView):
    serializer_class = DuelAwardSerializer

    def perform(self, data, contest_id, user):
        return services.award_duel(contest_id, data['winner'], user=user)


class AwardCustomView(OwnerActionView):
    serializer_class = CustomAwardSerializer

    def perform(self, data, contest_id, user):
        return services.award_custom(contest_id, data['winners'], data['amounts_eth'], user=user)


class WithdrawView(OwnerActionView):
    serializer_class = WithdrawSerializer

    def perform(self, data, contest_id, user):
        return services.withdraw_owner_share(contest_id, data['to'], user=user)


class PauseView(OwnerActionView):
    def perform(self, data, contest_id, user):
        return services.pause(user=user)


class UnpauseView(OwnerActionView):
    def perform(self, data, contest_id, user):
        return services.unpause(user=user)


class OwnerInfoView(BlockchainAPIView):
    """Server wallet address / balance (it pays the gas) and whether it owns the contract."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(services.owner_info())


class TransactionListView(BlockchainAPIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = ContractTransaction.objects.select_related('created_by')
        contest_id = request.query_params.get('contest_id')
        if contest_id is not None:
            if not contest_id.isdigit():
                return Response({'error': 'invalid_input', 'detail': 'contest_id نامعتبر است.'}, status=400)
            qs = qs.filter(contest_id=int(contest_id))
        if request.query_params.get('status'):
            qs = qs.filter(status=request.query_params['status'])
        return Response(ContractTransactionSerializer(qs[:100], many=True).data)


class TransactionDetailView(BlockchainAPIView):
    """Returns the transaction after refreshing its status from the chain."""

    permission_classes = [IsAdminUser]

    def get(self, request, tx_hash):
        tx = get_object_or_404(ContractTransaction, tx_hash=tx_hash.lower())
        return Response(ContractTransactionSerializer(services.refresh_transaction(tx)).data)
