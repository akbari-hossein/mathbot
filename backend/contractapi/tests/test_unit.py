"""Tests that do not need a blockchain node."""
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from eth_abi import encode as abi_encode
from eth_utils import keccak
from rest_framework.test import APIClient
from web3 import Web3

from contractapi import services
from contractapi.client import checksum, decode_revert, from_wei, load_abi, to_wei
from contractapi.errors import CONTRACT_ERROR_MESSAGES, ContractRevert, InvalidInput

User = get_user_model()

NOT_CONFIGURED = {
    'RPC_URL': '',
    'CHAIN_ID': 11155111,
    'CONTRACT_ADDRESS': '',
    'OWNER_PRIVATE_KEY': '',
    'EXPLORER_URL': 'https://sepolia.etherscan.io',
    'RPC_TIMEOUT': 5,
    'GAS_MULTIPLIER': 1.2,
}
WALLET = '0x' + 'ab' * 20


def _revert_data(signature, types=(), values=()):
    return '0x' + (keccak(text=signature)[:4] + abi_encode(list(types), list(values))).hex()


class DecodeRevertTests(TestCase):
    def test_custom_error_with_args(self):
        err = decode_revert(_revert_data('ContestNotFound(uint256)', ['uint256'], [5]))
        self.assertIsInstance(err, ContractRevert)
        self.assertEqual(err.code, 'ContestNotFound')
        self.assertEqual(err.args_dict, {'id': '5'})
        self.assertEqual(err.message, CONTRACT_ERROR_MESSAGES['ContestNotFound'])
        self.assertEqual(err.http_status, 400)

    def test_custom_error_with_address(self):
        err = decode_revert(
            _revert_data('AlreadyRegistered(uint256,address)', ['uint256', 'address'], [3, WALLET])
        )
        self.assertEqual(err.code, 'AlreadyRegistered')
        self.assertEqual(err.args_dict['user'].lower(), WALLET)

    def test_inherited_openzeppelin_errors_are_known(self):
        self.assertEqual(decode_revert(_revert_data('EnforcedPause()')).code, 'EnforcedPause')
        err = decode_revert(_revert_data('OwnableUnauthorizedAccount(address)', ['address'], [WALLET]))
        self.assertEqual(err.code, 'OwnableUnauthorizedAccount')

    def test_error_string_and_panic(self):
        err = decode_revert(_revert_data('Error(string)', ['string'], ['boom']))
        self.assertEqual((err.code, err.args_dict), ('Error', {'reason': 'boom'}))
        err = decode_revert(_revert_data('Panic(uint256)', ['uint256'], [0x11]))
        self.assertEqual((err.code, err.args_dict), ('Panic', {'code': '17'}))

    def test_unknown_selector(self):
        self.assertEqual(decode_revert('0xdeadbeef').code, 'UnknownRevert')

    def test_every_abi_error_has_a_message(self):
        names = {item['name'] for item in load_abi() if item['type'] == 'error'}
        self.assertEqual(names - set(CONTRACT_ERROR_MESSAGES), set())


class UnitConversionTests(TestCase):
    def test_to_wei(self):
        self.assertEqual(to_wei('0.05'), 5 * 10**16)
        self.assertEqual(to_wei(Decimal('1')), 10**18)
        self.assertEqual(to_wei(0), 0)
        self.assertEqual(to_wei('0.000000000000000001'), 1)
        self.assertEqual(to_wei('123456789012.123456789012345678'), 123456789012123456789012345678)

    def test_to_wei_rejects_bad_values(self):
        for value in ['-1', 'abc', '0.0000000000000000001', 'NaN', 'Infinity', '']:
            with self.subTest(value=value), self.assertRaises(InvalidInput):
                to_wei(value)

    def test_from_wei(self):
        self.assertEqual(from_wei(1500000000000000000), '1.5')
        self.assertEqual(from_wei(0), '0')
        self.assertEqual(from_wei(1), '0.000000000000000001')
        self.assertEqual(from_wei(10**30), '1000000000000')

    def test_checksum(self):
        self.assertEqual(checksum(WALLET), Web3.to_checksum_address(WALLET))
        self.assertNotEqual(checksum(WALLET), WALLET)
        for value in ['0x123', 'hello', None, 12]:
            with self.subTest(value=value), self.assertRaises(InvalidInput):
                checksum(value)

    def test_timestamp(self):
        aware = datetime(2030, 1, 1, tzinfo=dt_timezone.utc)
        self.assertEqual(services._timestamp(aware), 1893456000)
        self.assertEqual(services._timestamp(1893456000), 1893456000)
        # naive datetimes are read in TIME_ZONE (Asia/Tehran, UTC+3:30)
        self.assertEqual(services._timestamp(datetime(2030, 1, 1, 3, 30)), 1893456000)
        with self.assertRaises(InvalidInput):
            services._timestamp('tomorrow')


@override_settings(BLOCKCHAIN=NOT_CONFIGURED)
class ApiWithoutBlockchainTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = User.objects.create_user('player', 'p@x.com', 'pass1234')
        self.admin = User.objects.create_user('boss', 'b@x.com', 'pass1234', is_staff=True)

    def test_config_is_public(self):
        res = self.api.get('/api/contract/config/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['configured'], False)
        self.assertEqual(res.json()['chain_id'], 11155111)

    def test_not_configured_returns_503(self):
        res = self.api.get('/api/contract/contests/1/')
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json()['error'], 'blockchain_not_configured')

    def test_admin_endpoints_need_login(self):
        res = self.api.post('/api/contract/admin/contests/1/cancel/')
        self.assertEqual(res.status_code, 401)

    def test_admin_endpoints_reject_normal_users(self):
        self.api.force_authenticate(self.user)
        urls = [
            '/api/contract/admin/contests/',
            '/api/contract/admin/contests/1/deadline/',
            '/api/contract/admin/contests/1/budget/',
            '/api/contract/admin/contests/1/cancel/',
            '/api/contract/admin/contests/1/refund/',
            '/api/contract/admin/contests/1/award/top3/',
            '/api/contract/admin/contests/1/award/percentage/',
            '/api/contract/admin/contests/1/award/fixed/',
            '/api/contract/admin/contests/1/award/duel/',
            '/api/contract/admin/contests/1/award/custom/',
            '/api/contract/admin/contests/1/withdraw/',
            '/api/contract/admin/pause/',
            '/api/contract/admin/unpause/',
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.api.post(url, {}, format='json').status_code, 403)
        for url in ['/api/contract/admin/owner/', '/api/contract/admin/transactions/']:
            with self.subTest(url=url):
                self.assertEqual(self.api.get(url).status_code, 403)

    def test_participant_status_needs_login(self):
        self.assertEqual(self.api.get(f'/api/contract/contests/1/participants/{WALLET}/').status_code, 401)

    def test_input_is_validated_before_touching_the_chain(self):
        self.api.force_authenticate(self.admin)
        cases = [
            ('/api/contract/admin/contests/', {'contest_id': -1, 'price_eth': '1', 'signup_deadline': 'x'}),
            ('/api/contract/admin/contests/1/budget/', {'amount_eth': '0'}),
            ('/api/contract/admin/contests/1/award/top3/', {'first': WALLET, 'second': WALLET, 'third': WALLET}),
            ('/api/contract/admin/contests/1/award/top3/', {'first': '0x12', 'second': WALLET, 'third': WALLET}),
            (
                '/api/contract/admin/contests/1/award/percentage/',
                {'first': '0x' + '1' * 40, 'second': '0x' + '2' * 40, 'third': '0x' + '3' * 40, 'percents': [60, 30, 20]},
            ),
            ('/api/contract/admin/contests/1/award/custom/', {'winners': [WALLET], 'amounts_eth': ['1', '2']}),
            ('/api/contract/admin/contests/1/award/fixed/', {'first': '0x' + '1' * 40, 'second': '0x' + '2' * 40, 'third': '0x' + '3' * 40, 'amounts_eth': ['1']}),
            ('/api/contract/admin/contests/1/refund/', {'wallets': []}),
            ('/api/contract/admin/contests/1/withdraw/', {'to': 'not-an-address'}),
            ('/api/contract/admin/contests/1/award/duel/', {}),
        ]
        for url, body in cases:
            with self.subTest(url=url, body=body):
                self.assertEqual(self.api.post(url, body, format='json').status_code, 400)

    def test_rpc_down_returns_502(self):
        conf = {**NOT_CONFIGURED, 'RPC_URL': 'http://127.0.0.1:1', 'CONTRACT_ADDRESS': WALLET}
        with self.settings(BLOCKCHAIN=conf):
            res = self.api.get('/api/contract/contests/1/')
        self.assertEqual(res.status_code, 502)
        self.assertEqual(res.json()['error'], 'rpc_unavailable')

    def test_swagger_schema_builds(self):
        self.client.force_login(self.admin)
        res = self.client.get('/swagger.json')
        self.assertEqual(res.status_code, 200)
        paths = res.json()['paths']
        self.assertIn('/contract/admin/contests/{contest_id}/award/top3/', paths)
        body = paths['/contract/admin/contests/{contest_id}/award/top3/']['post']['parameters']
        self.assertTrue(any(p.get('in') == 'body' for p in body))

    def test_valid_admin_request_without_config_returns_503(self):
        self.api.force_authenticate(self.admin)
        res = self.api.post('/api/contract/admin/contests/1/cancel/')
        self.assertEqual(res.status_code, 503)

    def test_transaction_list_is_empty(self):
        self.api.force_authenticate(self.admin)
        res = self.api.get('/api/contract/admin/transactions/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])
        self.assertEqual(self.api.get('/api/contract/admin/transactions/?contest_id=abc').status_code, 400)
