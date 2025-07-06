from web3 import Web3
from .contract_config import contract_address, contract_abi
import os
import json
from dotenv import load_dotenv

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
OWNER_ADDRESS = os.getenv("OWNER_ADDRESS")
RPC_URL = os.getenv("RPC_URL")

address_node = Web3(Web3.HTTPProvider(RPC_URL))
w3 = Web3(address_node)
contract = address_node.eth.contract(address=contract_address, abi=contract_abi)

# create a transaction to send ether to the contract from user get user address and component price
def create_Tx_metamask(value , user_address):
    tx = {
      'to' : contract_address,
      'value' : hex(w3.to_wei(value , 'ether')),
      'gas' :  hex(100000),                     
      'gasPrice' :hex(w3.eth.gas_price),
      'nonce' :  w3.eth.get_transaction_count(user_address),
      'chainId' : 56
    }
    return json.dumps(tx)

