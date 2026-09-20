"""End-to-end tests against a real node (anvil). They deploy the compiled contract and use the HTTP API.

    cd contracts/Contest_prize && forge build && anvil      # in another terminal
    BLOCKCHAIN_TEST_RPC_URL=http://127.0.0.1:8545 python manage.py test contractapi
"""
import json
import os
import threading
import time
import unittest
from datetime import datetime, timezone as dt_timezone
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from eth_account import Account
from rest_framework.test import APIClient
from web3 import Web3

from contractapi import services
from contractapi.client import load_abi
from contractapi.models import ContractTransaction

User = get_user_model()

RPC_URL = os.environ.get('BLOCKCHAIN_TEST_RPC_URL')
ARTIFACT = Path(settings.BASE_DIR).parent / 'contracts' / 'Contest_prize' / 'out' / 'ContestPrize.sol' / 'ContestPrize.json'
ETH = 10**18


def fund(w3, address, eth=100):
    w3.provider.make_request('anvil_setBalance', [address, hex(eth * ETH)])


def new_account(w3, eth=100):
    acct = Account.create()
    fund(w3, acct.address, eth)
    return acct


def send_as(w3, acct, fn, value=0, wait=True):
    tx = fn.build_transaction(
        {
            'from': acct.address,
            'value': value,
            'nonce': w3.eth.get_transaction_count(acct.address, 'pending'),
            'chainId': w3.eth.chain_id,
        }
    )
    tx_hash = w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash) if wait else tx_hash.to_0x_hex()


@unittest.skipUnless(RPC_URL, 'set BLOCKCHAIN_TEST_RPC_URL (e.g. anvil) to run the on-chain tests')
class OnChainTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not ARTIFACT.exists():
            raise unittest.SkipTest('run `forge build` in contracts/Contest_prize first')
        artifact = json.loads(ARTIFACT.read_text(encoding='utf-8'))
        cls.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        cls.owner = new_account(cls.w3, 1000)
        receipt = send_as(
            cls.w3, cls.owner, cls.w3.eth.contract(abi=artifact['abi'], bytecode=artifact['bytecode']['object']).constructor()
        )
        cls.address = receipt['contractAddress']
        cls.contract = cls.w3.eth.contract(address=cls.address, abi=artifact['abi'])
        cls.artifact_abi = artifact['abi']
        cls.conf = {
            'RPC_URL': RPC_URL,
            'CHAIN_ID': cls.w3.eth.chain_id,
            'CONTRACT_ADDRESS': cls.address,
            'OWNER_PRIVATE_KEY': cls.owner.key.hex(),
            'EXPLORER_URL': 'https://sepolia.etherscan.io',
            'RPC_TIMEOUT': 10,
            'GAS_MULTIPLIER': 1.2,
        }
        cls._settings = override_settings(BLOCKCHAIN=cls.conf)
        cls._settings.enable()
        cls.next_id = 1000

    @classmethod
    def tearDownClass(cls):
        cls._settings.disable()
        super().tearDownClass()

    def setUp(self):
        self.api = APIClient()
        self.admin = User.objects.create_user('admin', 'a@x.com', 'pass1234', is_staff=True)
        self.player = User.objects.create_user('player', 'p@x.com', 'pass1234')
        self.api.force_authenticate(self.admin)
        # the node is shared by the whole class, so clean up what a previous test may have left
        self.w3.provider.make_request('evm_setAutomine', [True])
        self.force_unpause()

    # helpers ------------------------------------------------------------

    def contest_id(self):
        OnChainTests.next_id += 1
        return OnChainTests.next_id

    def deadline(self, seconds=86400):
        ts = self.w3.eth.get_block('latest')['timestamp'] + seconds
        return datetime.fromtimestamp(ts, tz=dt_timezone.utc).isoformat()

    def admin_post(self, url, body=None, expect=202):
        res = self.api.post(url, body or {}, format='json')
        self.assertEqual(res.status_code, expect, res.content)
        data = res.json()
        if expect == 202:
            # 202 only means "sent": wait for the receipt instead of assuming it is already mined
            services.wait_for_transaction(ContractTransaction.objects.get(tx_hash=data['tx_hash']), timeout=60)
            detail = self.api.get(f"/api/contract/admin/transactions/{data['tx_hash']}/").json()
            self.assertEqual(detail['status'], 'success', detail)
        return data

    def force_unpause(self):
        """A failed test must not leave the contract paused for the rest of the suite."""
        if self.contract.functions.paused().call():
            send_as(self.w3, self.owner, self.contract.functions.unpause())

    def create(self, cid, price_eth='0.01', budget_eth='0'):
        return self.admin_post(
            '/api/contract/admin/contests/',
            {'contest_id': cid, 'price_eth': price_eth, 'signup_deadline': self.deadline(), 'budget_eth': budget_eth},
        )

    def signup(self, player, cid, user_id, price_wei, wait=True):
        return send_as(self.w3, player, self.contract.functions.signup(cid, user_id), value=price_wei, wait=wait)

    def balance(self, address):
        return self.w3.eth.get_balance(address)

    # tests --------------------------------------------------------------

    def test_backend_abi_matches_compiled_contract(self):
        self.assertEqual(load_abi(), self.artifact_abi, 'run contracts/Contest_prize/script/export-abi.sh')

    def test_config_and_owner_info(self):
        config = self.api.get('/api/contract/config/').json()
        self.assertEqual(config['contract_address'], self.address)
        self.assertTrue(config['configured'])
        info = self.api.get('/api/contract/admin/owner/').json()
        self.assertEqual(info['server_wallet'], self.owner.address)
        self.assertTrue(info['server_wallet_is_owner'])
        self.assertFalse(info['paused'])

    def test_paid_contest_full_flow(self):
        cid = self.contest_id()
        tx = self.create(cid, price_eth='0.01')
        self.assertEqual(tx['action'], 'Addcomp')
        self.assertEqual(tx['contest_id'], cid)
        self.assertTrue(tx['explorer_url'].endswith(tx['tx_hash']))

        info = self.api.get(f'/api/contract/contests/{cid}/').json()
        self.assertEqual(info['state'], 'active')
        self.assertEqual(info['price_eth'], '0.01')
        self.assertEqual(info['price_wei'], str(10**16))
        self.assertTrue(info['signup_open'])

        # 4 players sign up from the "frontend"
        players = [new_account(self.w3) for _ in range(4)]
        signup_receipt = None
        for i, p in enumerate(players):
            signup_receipt = self.signup(p, cid, self.player.id if i == 0 else 500 + i, 10**16)

        # backend verification
        self.assertTrue(services.verify_signup(cid, players[0].address, self.player.id))
        self.assertTrue(
            services.verify_signup(cid, players[3].address, 503, tx_hash=signup_receipt['transactionHash'].to_0x_hex())
        )
        self.assertFalse(services.verify_signup(cid, players[0].address, 999))
        self.assertFalse(services.verify_signup(cid, new_account(self.w3).address, self.player.id))

        user_api = APIClient()
        user_api.force_authenticate(self.player)
        status = user_api.get(f'/api/contract/contests/{cid}/participants/{players[0].address.lower()}/').json()
        self.assertEqual(status, {'contest_id': cid, 'wallet': players[0].address, 'registered': True, 'is_current_user': True})
        status = user_api.get(f'/api/contract/contests/{cid}/participants/{players[1].address}/').json()
        self.assertEqual((status['registered'], status['is_current_user']), (True, False))

        info = self.api.get(f'/api/contract/contests/{cid}/').json()
        self.assertEqual((info['participants'], info['total_eth']), (4, '0.04'))

        before = [self.balance(p.address) for p in players[:3]]
        self.admin_post(
            f'/api/contract/admin/contests/{cid}/award/top3/',
            {'first': players[0].address, 'second': players[1].address, 'third': players[2].address},
        )
        gained = [self.balance(p.address) - b for p, b in zip(players[:3], before)]
        self.assertEqual(gained, [12 * 10**15, 8 * 10**15, 4 * 10**15])  # 30/20/10 % of 0.04

        info = self.api.get(f'/api/contract/contests/{cid}/').json()
        self.assertEqual((info['state'], info['total_eth'], info['signup_open']), ('finished', '0.016', False))

        treasury = Account.create().address
        self.admin_post(f'/api/contract/admin/contests/{cid}/withdraw/', {'to': treasury})
        self.assertEqual(self.balance(treasury), 16 * 10**15)

        txs = self.api.get(f'/api/contract/admin/transactions/?contest_id={cid}').json()
        self.assertEqual([t['action'] for t in txs], ['withdrawOwner', 'Awardwinners', 'Addcomp'])
        self.assertTrue(all(t['created_by'] == 'admin' for t in txs))

    def test_contract_errors_are_readable(self):
        cid = self.contest_id()
        self.create(cid)
        res = self.api.post(
            '/api/contract/admin/contests/',
            {'contest_id': cid, 'price_eth': '1', 'signup_deadline': self.deadline()},
            format='json',
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error'], 'ContestAlreadyExists')
        self.assertEqual(res.json()['details']['args'], {'id': str(cid)})
        self.assertIn('قبلا', res.json()['detail'])

        res = self.api.post('/api/contract/admin/contests/999999/cancel/')
        self.assertEqual((res.status_code, res.json()['error']), (400, 'ContestNotFound'))

        res = self.api.post(
            '/api/contract/admin/contests/',
            {'contest_id': self.contest_id(), 'price_eth': '1', 'signup_deadline': '2001-01-01T00:00:00Z'},
            format='json',
        )
        self.assertEqual(res.json()['error'], 'InvalidDeadline')

        res = self.api.post(f'/api/contract/admin/contests/{cid}/withdraw/', {'to': self.owner.address}, format='json')
        self.assertEqual(res.json()['error'], 'ContestStillActive')

        # a rejected transaction is never sent, so nothing is logged
        self.assertEqual(ContractTransaction.objects.filter(contest_id=cid).count(), 1)

        self.assertEqual(self.api.get('/api/contract/contests/999999/').status_code, 404)

    def test_cancel_and_refund(self):
        cid = self.contest_id()
        self.create(cid, price_eth='0.5', budget_eth='1')
        players = [new_account(self.w3) for _ in range(2)]
        for i, p in enumerate(players):
            self.signup(p, cid, 700 + i, ETH // 2)
        self.admin_post(f'/api/contract/admin/contests/{cid}/cancel/')
        self.assertEqual(self.api.get(f'/api/contract/contests/{cid}/').json()['state'], 'cancelled')

        before = [self.balance(p.address) for p in players]
        self.admin_post(f'/api/contract/admin/contests/{cid}/refund/', {'wallets': [p.address for p in players]})
        self.assertEqual([self.balance(p.address) - b for p, b in zip(players, before)], [ETH // 2, ETH // 2])

        # the budget (1 ETH) is left for the owner
        treasury = Account.create().address
        self.admin_post(f'/api/contract/admin/contests/{cid}/withdraw/', {'to': treasury})
        self.assertEqual(self.balance(treasury), ETH)
        self.assertEqual(self.api.get(f'/api/contract/contests/{cid}/').json()['total_wei'], '0')

    def test_free_contest_budget_and_awards(self):
        cid = self.contest_id()
        self.create(cid, price_eth='0', budget_eth='0.5')
        self.admin_post(f'/api/contract/admin/contests/{cid}/budget/', {'amount_eth': '0.25'})
        info = self.api.get(f'/api/contract/contests/{cid}/').json()
        self.assertEqual((info['is_free'], info['total_eth']), (True, '0.75'))

        w = [Account.create().address for _ in range(3)]
        res = self.api.post(
            f'/api/contract/admin/contests/{cid}/award/fixed/',
            {'first': w[0], 'second': w[1], 'third': w[2], 'amounts_eth': ['0.5', '0.2', '0.1']},
            format='json',
        )
        self.assertEqual(res.json()['error'], 'InsufficientContestBalance')
        self.admin_post(
            f'/api/contract/admin/contests/{cid}/award/fixed/',
            {'first': w[0], 'second': w[1], 'third': w[2], 'amounts_eth': ['0.4', '0.2', '0.1']},
        )
        self.assertEqual([self.balance(a) for a in w], [4 * 10**17, 2 * 10**17, 10**17])

    def test_percentage_duel_and_custom_awards(self):
        w = [Account.create().address for _ in range(4)]

        cid = self.contest_id()
        self.create(cid, price_eth='0', budget_eth='1')
        self.admin_post(
            f'/api/contract/admin/contests/{cid}/award/percentage/',
            {'first': w[0], 'second': w[1], 'third': w[2], 'percents': [50, 25, 5]},
        )
        self.assertEqual([self.balance(a) for a in w[:3]], [ETH // 2, ETH // 4, ETH // 20])

        cid = self.contest_id()
        self.create(cid, price_eth='0', budget_eth='1')
        self.admin_post(f'/api/contract/admin/contests/{cid}/award/duel/', {'winner': w[3]})
        self.assertEqual(self.balance(w[3]), 9 * ETH // 10)

        cid = self.contest_id()
        self.create(cid, price_eth='0', budget_eth='1')
        self.admin_post(
            f'/api/contract/admin/contests/{cid}/award/custom/',
            {'winners': [w[0], w[1]], 'amounts_eth': ['0.3', '0.7']},
        )
        self.assertEqual(self.balance(w[0]), ETH // 2 + 3 * ETH // 10)
        self.assertEqual(self.api.get(f'/api/contract/contests/{cid}/').json()['total_wei'], '0')

    def test_signup_deadline(self):
        cid = self.contest_id()
        self.create(cid)
        self.w3.provider.make_request('evm_increaseTime', [2 * 86400])
        self.w3.provider.make_request('evm_mine', [])
        self.assertFalse(self.api.get(f'/api/contract/contests/{cid}/').json()['signup_open'])
        self.admin_post(f'/api/contract/admin/contests/{cid}/deadline/', {'signup_deadline': self.deadline(3600)})
        self.assertTrue(self.api.get(f'/api/contract/contests/{cid}/').json()['signup_open'])

    def test_pause_blocks_admin_actions(self):
        self.addCleanup(self.force_unpause)
        self.admin_post('/api/contract/admin/pause/')
        try:
            self.assertTrue(self.api.get('/api/contract/admin/owner/').json()['paused'])
            res = self.api.post(
                '/api/contract/admin/contests/',
                {'contest_id': self.contest_id(), 'price_eth': '1', 'signup_deadline': self.deadline()},
                format='json',
            )
            self.assertEqual(res.json()['error'], 'EnforcedPause')
        finally:
            self.admin_post('/api/contract/admin/unpause/')
        self.create(self.contest_id())

    def test_verify_signup_waits_for_pending_transaction(self):
        cid = self.contest_id()
        self.create(cid)
        player = new_account(self.w3)
        self.w3.provider.make_request('evm_setAutomine', [False])
        try:
            tx_hash = self.signup(player, cid, 42, 10**16, wait=False)
            self.assertFalse(services.verify_signup(cid, player.address, 42))  # not mined yet
            result = {}
            worker = threading.Thread(
                target=lambda: result.setdefault('ok', services.verify_signup(cid, player.address, 42, tx_hash=tx_hash))
            )
            worker.start()
            time.sleep(1.5)
            self.w3.provider.make_request('evm_mine', [])
            worker.join(timeout=30)
            self.assertTrue(result.get('ok'))
        finally:
            self.w3.provider.make_request('evm_setAutomine', [True])

    def test_back_to_back_transactions_get_their_own_nonce(self):
        self.w3.provider.make_request('evm_setAutomine', [False])
        try:
            ids = [self.contest_id(), self.contest_id(), self.contest_id()]
            txs = [services.create_contest(i, '0.01', self.w3.eth.get_block('latest')['timestamp'] + 3600) for i in ids]
            self.assertEqual(len({t.tx_hash for t in txs}), 3)
            self.w3.provider.make_request('evm_mine', [])
        finally:
            self.w3.provider.make_request('evm_setAutomine', [True])
        for t in txs:
            self.assertEqual(services.refresh_transaction(t).status, 'success')
        for i in ids:
            self.assertEqual(services.get_contest(i)['state'], 'active')

    def test_server_wallet_that_is_not_owner(self):
        stranger = new_account(self.w3)
        with self.settings(BLOCKCHAIN={**self.conf, 'OWNER_PRIVATE_KEY': stranger.key.hex()}):
            res = self.api.post(
                '/api/contract/admin/contests/',
                {'contest_id': self.contest_id(), 'price_eth': '1', 'signup_deadline': self.deadline()},
                format='json',
            )
            self.assertEqual(res.json()['error'], 'OwnableUnauthorizedAccount')
            self.assertFalse(self.api.get('/api/contract/admin/owner/').json()['server_wallet_is_owner'])

    def test_misconfiguration_is_detected(self):
        with self.settings(BLOCKCHAIN={**self.conf, 'CHAIN_ID': 1}):
            res = self.api.get('/api/contract/contests/1/')
            self.assertEqual(res.status_code, 503)
            self.assertIn('chain id', res.json()['detail'])
        with self.settings(BLOCKCHAIN={**self.conf, 'CONTRACT_ADDRESS': self.owner.address}):
            res = self.api.get('/api/contract/contests/1/')
            self.assertEqual(res.status_code, 503)
        with self.settings(BLOCKCHAIN={**self.conf, 'OWNER_PRIVATE_KEY': ''}):
            res = self.api.post(f'/api/contract/admin/contests/{self.contest_id()}/cancel/')
            self.assertEqual(res.status_code, 503)
