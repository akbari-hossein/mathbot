"""Low level access to the ContestPrize contract (web3.py 7).

Nothing here talks to the network at import time: the connection is created on first use,
so Django starts even when the RPC is down or the blockchain settings are empty.
Other apps should use `contractapi.services`, not this module.
"""
import json
import threading
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, localcontext
from functools import lru_cache
from pathlib import Path

import requests
from django.conf import settings
from eth_abi import decode as abi_decode
from eth_account import Account
from eth_utils import keccak
from web3 import Web3
from web3.exceptions import (
    ContractCustomError,
    ContractLogicError,
    ContractPanicError,
    ProviderConnectionError,
    TimeExhausted,
    TransactionNotFound,
    Web3RPCError,
)
from web3.middleware import ExtraDataToPOAMiddleware

from .errors import (
    BlockchainError,
    BlockchainNotConfigured,
    BlockchainUnavailable,
    ContractRevert,
    InvalidInput,
)

# Generated from the Solidity source by contracts/Contest_prize/script/export-abi.sh
ABI_PATH = Path(__file__).resolve().parent / 'abi' / 'ContestPrize.json'

ERROR_STRING_SELECTOR = bytes.fromhex('08c379a0')  # Error(string)
PANIC_SELECTOR = bytes.fromhex('4e487b71')  # Panic(uint256)


@lru_cache(maxsize=1)
def load_abi():
    return json.loads(ABI_PATH.read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def _error_table():
    """selector -> (error name, [input names], [input types]) for every error in the ABI."""
    table = {}
    for item in load_abi():
        if item.get('type') != 'error':
            continue
        types = [i['type'] for i in item['inputs']]
        signature = f"{item['name']}({','.join(types)})"
        table[keccak(text=signature)[:4]] = (item['name'], [i['name'] for i in item['inputs']], types)
    return table


def _jsonable(value):
    if isinstance(value, bytes):
        return '0x' + value.hex()
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)  # uint256 does not fit in a JS number
    return value


def decode_revert(data):
    """Turns revert data (hex string or bytes) into a ContractRevert exception."""
    if isinstance(data, str):
        data = bytes.fromhex(data[2:] if data.startswith('0x') else data)
    data = data or b''
    selector, payload = data[:4], data[4:]

    if selector in _error_table():
        name, names, types = _error_table()[selector]
        try:
            values = abi_decode(types, payload)
        except Exception:
            values = ()
        return ContractRevert(name, {n or f'arg{i}': _jsonable(v) for i, (n, v) in enumerate(zip(names, values))})
    if selector == ERROR_STRING_SELECTOR:
        try:
            (reason,) = abi_decode(['string'], payload)
        except Exception:
            reason = ''
        return ContractRevert('Error', {'reason': reason})
    if selector == PANIC_SELECTOR:
        return ContractRevert('Panic', {'code': _jsonable(int.from_bytes(payload[:32], 'big'))})
    return ContractRevert('UnknownRevert', raw='0x' + data.hex() if data else None)


def to_wei(amount_eth):
    """'0.05' / Decimal / int (ETH) -> int (wei). Rejects negatives and more than 18 decimals."""
    with localcontext() as ctx:
        ctx.prec = 100  # exact for any uint256 amount
        try:
            amount = Decimal(str(amount_eth).strip())
        except (InvalidOperation, ValueError):
            raise InvalidInput(f'مبلغ نامعتبر است: {amount_eth}')
        if not amount.is_finite() or amount < 0:
            raise InvalidInput(f'مبلغ نامعتبر است: {amount_eth}')
        wei = amount.scaleb(18)
        if wei != wei.to_integral_value():
            raise InvalidInput(f'مبلغ بیشتر از ۱۸ رقم اعشار دارد: {amount_eth}')
        return int(wei)


def from_wei(amount_wei):
    """int (wei) -> str (ETH) without float rounding, e.g. 1500000000000000000 -> '1.5'."""
    with localcontext() as ctx:
        ctx.prec = 100
        value = Decimal(int(amount_wei)).scaleb(-18).normalize()
        return format(value, 'f')


def checksum(address):
    if not isinstance(address, str) or not Web3.is_address(address):
        raise InvalidInput(f'آدرس کیف پول نامعتبر است: {address}')
    return Web3.to_checksum_address(address)


def _is_nonce_error(exc):
    text = str(exc).lower()
    return any(s in text for s in ('nonce too low', 'already known', 'replacement transaction underpriced'))


@contextmanager
def translate_errors():
    """Converts web3 / requests exceptions into BlockchainError subclasses."""
    try:
        yield
    except BlockchainError:
        raise
    except (ContractCustomError, ContractLogicError) as exc:
        data = getattr(exc, 'data', None)
        if isinstance(data, str) and data.startswith('0x') and len(data) >= 10:
            raise decode_revert(data) from exc
        if isinstance(exc, ContractPanicError):
            raise ContractRevert('Panic', raw=str(exc)) from exc
        reason = str(getattr(exc, 'message', '') or exc).replace('execution reverted:', '').strip()
        raise ContractRevert('Error', {'reason': reason} if reason else None) from exc
    except Web3RPCError as exc:
        text = str(exc).lower()
        if 'insufficient funds' in text:
            raise BlockchainError(
                'موجودی کیف پول سرور برای کارمزد تراکنش کافی نیست.', code='owner_insufficient_funds'
            ) from exc
        raise BlockchainError(f'خطای شبکه بلاکچین: {exc}', code='rpc_error') from exc
    except (requests.exceptions.RequestException, ProviderConnectionError, ConnectionError, TimeoutError) as exc:
        raise BlockchainUnavailable() from exc


class ContestContract:
    def __init__(self, conf):
        rpc_url = conf.get('RPC_URL')
        address = conf.get('CONTRACT_ADDRESS')
        if not rpc_url or not address:
            raise BlockchainNotConfigured(
                'BLOCKCHAIN_RPC_URL و CONTEST_CONTRACT_ADDRESS در فایل .env بک‌اند تنظیم نشده‌اند.'
            )
        if not Web3.is_address(address):
            raise BlockchainNotConfigured('CONTEST_CONTRACT_ADDRESS یک آدرس معتبر نیست.')

        self.chain_id = int(conf.get('CHAIN_ID'))
        self.gas_multiplier = float(conf.get('GAS_MULTIPLIER', 1.2))
        self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': conf.get('RPC_TIMEOUT', 20)}))
        # needed on PoA chains (BSC, Polygon...), harmless elsewhere
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self.address = Web3.to_checksum_address(address)
        self.contract = self.w3.eth.contract(address=self.address, abi=load_abi())

        key = conf.get('OWNER_PRIVATE_KEY')
        try:
            self.owner = Account.from_key(key) if key else None
        except Exception:
            raise BlockchainNotConfigured('BLOCKCHAIN_OWNER_PRIVATE_KEY نامعتبر است.')

        self._send_lock = threading.Lock()
        self._checked = False

    def check_connection(self):
        """Once per process: right network and a contract at the address."""
        if self._checked:
            return
        with translate_errors():
            rpc_chain_id = self.w3.eth.chain_id
            if rpc_chain_id != self.chain_id:
                raise BlockchainNotConfigured(
                    f'شبکه RPC (chain id {rpc_chain_id}) با BLOCKCHAIN_CHAIN_ID ({self.chain_id}) یکی نیست.'
                )
            if not self.w3.eth.get_code(self.address):
                raise BlockchainNotConfigured(f'در آدرس {self.address} قراردادی روی این شبکه وجود ندارد.')
        self._checked = True

    def call(self, fn_name, *args):
        self.check_connection()
        with translate_errors():
            return getattr(self.contract.functions, fn_name)(*args).call()

    def send(self, fn_name, *args, value=0):
        """Simulates, signs and sends an owner transaction. Returns the tx hash (0x...).

        The simulation (estimate_gas) makes the contract errors show up here, before any gas is spent.
        """
        if self.owner is None:
            raise BlockchainNotConfigured('BLOCKCHAIN_OWNER_PRIVATE_KEY برای تراکنش‌های مدیریتی تنظیم نشده است.')
        self.check_connection()
        fn = getattr(self.contract.functions, fn_name)(*args)
        base = {'from': self.owner.address, 'value': int(value)}

        with translate_errors():
            gas = int(fn.estimate_gas(base) * self.gas_multiplier)
            base['chainId'] = self.chain_id
            fees = {}
            if 'baseFeePerGas' not in self.w3.eth.get_block('latest'):
                fees['gasPrice'] = self.w3.eth.gas_price  # chain without EIP-1559

            # one transaction at a time per process, so two requests never get the same nonce
            with self._send_lock:
                for attempt in range(2):
                    nonce = self.w3.eth.get_transaction_count(self.owner.address, 'pending')
                    tx = fn.build_transaction({**base, **fees, 'gas': gas, 'nonce': nonce})
                    signed = self.owner.sign_transaction(tx)
                    try:
                        return self.w3.eth.send_raw_transaction(signed.raw_transaction).to_0x_hex()
                    except Web3RPCError as exc:
                        if attempt == 0 and _is_nonce_error(exc):
                            continue
                        raise

    def receipt(self, tx_hash):
        """Receipt of a mined transaction, or None while it is pending."""
        self.check_connection()
        with translate_errors():
            try:
                return self.w3.eth.get_transaction_receipt(tx_hash)
            except TransactionNotFound:
                return None

    def wait(self, tx_hash, timeout):
        """Waits up to `timeout` seconds for the receipt, returns None on timeout."""
        self.check_connection()
        with translate_errors():
            try:
                return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout, poll_latency=1)
            except TimeExhausted:
                return None

    def balance(self, address):
        self.check_connection()
        with translate_errors():
            return self.w3.eth.get_balance(address)


_client = None
_client_conf = None
_client_lock = threading.Lock()


def get_client():
    """Shared ContestContract built from settings.BLOCKCHAIN (rebuilt if the settings change)."""
    global _client, _client_conf
    conf = dict(settings.BLOCKCHAIN)
    with _client_lock:
        if _client is None or conf != _client_conf:
            _client = ContestContract(conf)
            _client_conf = conf
        return _client
