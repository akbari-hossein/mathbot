"""High level API of the ContestPrize contract - use these functions from views and other apps.

    from contractapi import services
    services.create_contest(contest.id, price_eth='0.01', signup_deadline=contest.start_time, user=request.user)
    services.verify_signup(contest.id, wallet_address, request.user.id, tx_hash=tx_hash)

Amounts are in ETH (str / Decimal) on the way in; wei values are returned as strings because
they do not fit in a JavaScript number. Every owner action returns the ContractTransaction it logged.
Errors are raised as contractapi.errors.BlockchainError subclasses (each one has code + Persian message).
"""
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from .client import checksum, from_wei, get_client, to_wei
from .errors import InvalidInput
from .models import ContractTransaction


# ----------------------------------------------------------------------
# read only
# ----------------------------------------------------------------------

def contract_config():
    """Public info the frontend needs to talk to the contract."""
    conf = settings.BLOCKCHAIN
    address = conf.get('CONTRACT_ADDRESS') or None
    try:
        address = checksum(address) if address else None
    except InvalidInput:
        address = None  # misconfigured address: report "not configured" instead of failing
    return {
        'configured': bool(conf.get('RPC_URL') and address),
        'chain_id': conf.get('CHAIN_ID'),
        'contract_address': address,
        'explorer_url': conf.get('EXPLORER_URL'),
    }


def get_contest(contest_id):
    """On-chain state of a contest, or None if it was never created on the contract."""
    client = get_client()
    contest_id = _contest_id(contest_id)
    if not client.call('getcompexist', contest_id):
        return None
    total, price, deadline, participants, active, _exist, cancelled = client.call('getcomp', contest_id)
    if active:
        state = 'active'
    elif cancelled:
        state = 'cancelled'
    else:
        state = 'finished'
    return {
        'contest_id': contest_id,
        'state': state,
        'price_wei': str(price),
        'price_eth': from_wei(price),
        'is_free': price == 0,
        'total_wei': str(total),
        'total_eth': from_wei(total),
        'participants': participants,
        'signup_deadline': deadline,
        'signup_deadline_iso': datetime.fromtimestamp(deadline, tz=timezone.get_current_timezone()).isoformat(),
        'signup_open': client.call('isSignupOpen', contest_id),
    }


def get_participant_ref(contest_id, wallet):
    """Backend user id that signed up with `wallet` in the contest (0 = not signed up)."""
    return get_client().call('getParticipantRef', _contest_id(contest_id), checksum(wallet))


def verify_signup(contest_id, wallet, user_id, tx_hash=None, wait_seconds=20):
    """True if `wallet` paid the signup of `contest_id` for backend user `user_id`.

    Call it before creating the Participation of a paid contest. If the frontend sends the
    signup tx hash, a transaction that is not mined yet (or an RPC node a block behind) is
    waited for up to `wait_seconds`.
    """
    user_id = int(user_id)
    if user_id <= 0:
        return False
    if get_participant_ref(contest_id, wallet) == user_id:
        return True
    if tx_hash:
        receipt = get_client().wait(_tx_hash(tx_hash), timeout=wait_seconds)
        if receipt is not None and receipt['status'] == 1:
            return get_participant_ref(contest_id, wallet) == user_id
    return False


def owner_info():
    """Server wallet (contract owner) address, balance and contract state - for the admin panel."""
    client = get_client()
    info = {'contract_address': client.address, 'paused': client.call('paused'), 'contract_owner': client.call('owner')}
    if client.owner is None:
        info.update({'server_wallet': None, 'server_wallet_balance_eth': None, 'server_wallet_is_owner': False})
    else:
        info.update(
            {
                'server_wallet': client.owner.address,
                'server_wallet_balance_eth': from_wei(client.balance(client.owner.address)),
                'server_wallet_is_owner': info['contract_owner'] == client.owner.address,
            }
        )
    return info


# ----------------------------------------------------------------------
# owner (admin) actions - each one sends a transaction and returns the ContractTransaction
# ----------------------------------------------------------------------

def create_contest(contest_id, price_eth, signup_deadline, budget_eth=0, user=None):
    """Registers a contest on the contract. price_eth=0 -> free contest (fund it with add_budget / budget_eth)."""
    contest_id = _contest_id(contest_id)
    price = to_wei(price_eth)
    budget = to_wei(budget_eth or 0)
    deadline = _timestamp(signup_deadline)
    return _send(
        'Addcomp',
        (contest_id, price, deadline),
        value=budget,
        contest_id=contest_id,
        params={'price_wei': str(price), 'signup_deadline': deadline, 'budget_wei': str(budget)},
        user=user,
    )


def set_signup_deadline(contest_id, signup_deadline, user=None):
    contest_id = _contest_id(contest_id)
    deadline = _timestamp(signup_deadline)
    return _send('setSignupDeadline', (contest_id, deadline), contest_id=contest_id, params={'signup_deadline': deadline}, user=user)


def add_budget(contest_id, amount_eth, user=None):
    contest_id = _contest_id(contest_id)
    amount = to_wei(amount_eth)
    if amount == 0:
        raise InvalidInput('مبلغ باید بیشتر از صفر باشد.')
    return _send('addbudgeforfreecomp', (contest_id,), value=amount, contest_id=contest_id, params={'amount_wei': str(amount)}, user=user)


def cancel_contest(contest_id, user=None):
    contest_id = _contest_id(contest_id)
    return _send('cancelComp', (contest_id,), contest_id=contest_id, user=user)


def refund_participants(contest_id, wallets, user=None):
    """Sends the entry fee back to these wallets (cancelled contests only). Unregistered wallets are skipped."""
    contest_id = _contest_id(contest_id)
    wallets = [checksum(w) for w in wallets]
    if not wallets:
        raise InvalidInput('لیست کیف پول‌ها خالی است.')
    return _send('refundParticipants', (contest_id, wallets), contest_id=contest_id, params={'wallets': wallets}, user=user)


def award_top3(contest_id, first, second, third, user=None):
    """30% / 20% / 10% of the contest balance, the other 40% stays for withdraw_owner_share."""
    contest_id = _contest_id(contest_id)
    winners = [checksum(first), checksum(second), checksum(third)]
    return _send('Awardwinners', (*winners, contest_id), contest_id=contest_id, params={'winners': winners}, user=user)


def award_with_percentage(contest_id, first, second, third, percents, user=None):
    contest_id = _contest_id(contest_id)
    winners = [checksum(first), checksum(second), checksum(third)]
    percents = [int(p) for p in percents]
    if len(percents) != 3 or min(percents) < 0 or sum(percents) > 100:
        raise InvalidInput('سه درصد نامنفی با مجموع حداکثر ۱۰۰ لازم است.')
    return _send(
        'AwardWithPercentage', (*winners, *percents, contest_id), contest_id=contest_id,
        params={'winners': winners, 'percents': percents}, user=user,
    )


def award_fixed(contest_id, first, second, third, amounts_eth, user=None):
    """Pays a fixed ETH amount to each of the top 3."""
    contest_id = _contest_id(contest_id)
    winners = [checksum(first), checksum(second), checksum(third)]
    if len(amounts_eth) != 3:
        raise InvalidInput('برای هر سه نفر مبلغ لازم است.')
    amounts = [to_wei(a) for a in amounts_eth]
    return _send(
        'Awardforfree_comp', (*winners, *amounts, contest_id), contest_id=contest_id,
        params={'winners': winners, 'amounts_wei': [str(a) for a in amounts]}, user=user,
    )


def award_duel(contest_id, winner, user=None):
    """90% of the contest balance to the winner of a duel."""
    contest_id = _contest_id(contest_id)
    winner = checksum(winner)
    return _send('Awardforduel_comp', (winner, contest_id), contest_id=contest_id, params={'winners': [winner]}, user=user)


def award_custom(contest_id, winners, amounts_eth, user=None):
    """Any number of winners with any ETH amounts."""
    contest_id = _contest_id(contest_id)
    winners = [checksum(w) for w in winners]
    amounts = [to_wei(a) for a in amounts_eth]
    if not winners or len(winners) != len(amounts):
        raise InvalidInput('تعداد برندگان و جوایز برابر نیست.')
    return _send(
        'Awardforarbitrary_comp', (winners, amounts, contest_id), contest_id=contest_id,
        params={'winners': winners, 'amounts_wei': [str(a) for a in amounts]}, user=user,
    )


def withdraw_owner_share(contest_id, to, user=None):
    """Sends what is left of a finished contest (or the budget of a cancelled one) to `to`."""
    contest_id = _contest_id(contest_id)
    to = checksum(to)
    return _send('withdrawOwner', (to, contest_id), contest_id=contest_id, params={'to': to}, user=user)


def pause(user=None):
    return _send('pause', (), user=user)


def unpause(user=None):
    return _send('unpause', (), user=user)


# ----------------------------------------------------------------------
# transactions
# ----------------------------------------------------------------------

def refresh_transaction(tx):
    """Updates a pending ContractTransaction from its receipt."""
    if tx.status != ContractTransaction.Status.PENDING:
        return tx
    receipt = get_client().receipt(tx.tx_hash)
    if receipt is not None:
        tx.status = ContractTransaction.Status.SUCCESS if receipt['status'] == 1 else ContractTransaction.Status.FAILED
        tx.block_number = receipt['blockNumber']
        tx.gas_used = receipt['gasUsed']
        tx.save(update_fields=['status', 'block_number', 'gas_used', 'updated_at'])
    return tx


def wait_for_transaction(tx, timeout=60):
    """Blocks until the transaction is mined (or timeout) and returns the refreshed ContractTransaction."""
    get_client().wait(tx.tx_hash, timeout=timeout)
    return refresh_transaction(tx)


def explorer_tx_url(tx_hash):
    base = (settings.BLOCKCHAIN.get('EXPLORER_URL') or '').rstrip('/')
    return f'{base}/tx/{tx_hash}' if base else None


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def _send(fn_name, args, value=0, contest_id=None, params=None, user=None):
    tx_hash = get_client().send(fn_name, *args, value=value)
    return ContractTransaction.objects.create(
        tx_hash=tx_hash,
        action=fn_name,
        contest_id=contest_id,
        params=params or {},
        created_by=user if getattr(user, 'is_authenticated', False) else None,
    )


def _contest_id(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise InvalidInput(f'شناسه مسابقه نامعتبر است: {value}')
    if value < 0:
        raise InvalidInput(f'شناسه مسابقه نامعتبر است: {value}')
    return value


def _timestamp(value):
    """datetime (aware or naive in TIME_ZONE) or unix seconds -> int unix seconds."""
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            value = timezone.make_aware(value)
        return int(value.timestamp())
    try:
        return int(value)
    except (TypeError, ValueError):
        raise InvalidInput(f'زمان نامعتبر است: {value}')


def _tx_hash(value):
    if not isinstance(value, str) or len(value) != 66 or not value.startswith('0x'):
        raise InvalidInput(f'هش تراکنش نامعتبر است: {value}')
    try:
        int(value, 16)
    except ValueError:
        raise InvalidInput(f'هش تراکنش نامعتبر است: {value}')
    return value.lower()
