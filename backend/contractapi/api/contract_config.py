from .web3_config_payment import address_node ,w3 , contract , OWNER_ADDRESS , PRIVATE_KEY
import json
from dotenv import load_dotenv
import os

contract_address = address_node.to_checksum_address("write address")
contract_abi = json.loads('ABI')
owner_address = address_node.to_checksum_address(OWNER_ADDRESS)
nonce_owner = w3.eth.get_transaction_count(owner_address)

def Createcomp(ID , Price):
    Price = address_node.to_wei(Price , 'ether')
    tx = contract.functions.Addcomp(int(ID) , Price).build_transaction({
        'from':owner_address ,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce_owner
    })
    sign_tx = w3.eth.account.sign_transaction(tx , PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(sign_tx.rawTransaction)
    return w3.to_hex(tx_hash)

def Createcompfree(ID):
    tx = contract.functions.Addfreecomp(int(ID)).build_transaction({
        'from':owner_address ,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce_owner
    })
    sign_tx = w3.eth.account.sign_transaction(tx , PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(sign_tx.rawTransaction)
    return w3.to_hex(tx_hash)

def Awardwinners(address_1 , address_2 , address_3 , ID ):
    tx = contract.functions.Awardwinners(address_1 , address_2 , address_3 , int(ID) ).build_transaction({
        'from':owner_address ,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce_owner
    })
    sign_tx = w3.eth.account.sign_transaction(tx , PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(sign_tx.rawTransaction)
    return w3.to_hex(tx_hash)

def AwardWithPercentage(address_1 , address_2 , address_3 ,percent_1 , percent_2 , percent_3 , ID ):
    tx = contract.functions.Awardwinners(address_1 , address_2 , address_3 ,int(percent_1) , int(percent_2) , int(percent_3) , int(ID) ).build_transaction({
        'from':owner_address ,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce_owner
    })
    sign_tx = w3.eth.account.sign_transaction(tx , PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(sign_tx.rawTransaction)
    return w3.to_hex(tx_hash)

def Awardforduel_comp(address_1 , ID ):
    tx = contract.functions.Awardforduel_comp(address_1 , int(ID) ).build_transaction({
        'from':owner_address ,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce_owner
    })
    sign_tx = w3.eth.account.sign_transaction(tx , PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(sign_tx.rawTransaction)
    return w3.to_hex(tx_hash)

def Awardforfree_comp(address_1 , address_2 , address_3 ,value_1 , value_2 , value_3 , ID ):
    value_1 = address_node.to_wei(value_1 , 'ether')
    value_2 = address_node.to_wei(value_2 , 'ether')
    value_3 = address_node.to_wei(value_3 , 'ether')
    tx = contract.functions.Awardforfree_comp(address_1 , address_2 , address_3 ,value_1 , value_2 , value_3 , int(ID) ).build_transaction({
        'from':owner_address ,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce_owner
    })
    sign_tx = w3.eth.account.sign_transaction(tx , PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(sign_tx.rawTransaction)
    return w3.to_hex(tx_hash)

def Awardforarbitrary_comp(winners_array , prize_array , ID):
    for i in range(len(prize_array)) :
        prize_array[i] = address_node.to_wei(prize_array[i] , 'ether')
    tx = contract.functions.Awardforarbitrary_comp(winners_array , prize_array , ID).build_transaction({
        'from':owner_address ,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce_owner

    })
    sign_tx = w3.eth.account.sign_transaction(tx , PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(sign_tx.rawTransaction)
    return w3.to_hex(tx_hash)

def withdrawOwner(address , ID):
    tx = contract.functions.withdrawOwner(address , int(ID)).build_transaction({
        'from':owner_address ,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce_owner
    })
    sign_tx = w3.eth.account.sign_transaction(tx , PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(sign_tx.rawTransaction)
    return w3.to_hex(tx_hash)

def comptotal(ID):
    total = contract.functions.getcomptotal(int(ID)).call()
    return total

def compstatus(ID):
    status = contract.functions.getcompstatus(int(ID)).call()
    return status

def compexist(ID):
    exist = contract.functions.getcompexist(int(ID)).call()
    return exist