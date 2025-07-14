from .web3_config_payment import address_node ,w3 , contract , OWNER_ADDRESS , PRIVATE_KEY
import json
from dotenv import load_dotenv
import os

contract_address = address_node.to_checksum_address("write address")
contract_abi = json.loads('ABI')
owner_address = address_node.to_checksum_address(OWNER_ADDRESS)
nonce_owner = w3.eth.get_transaction_count(owner_address)

# When the admin wants to create a new contest, must call this function via the API.
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

# When the admin wants to create a new contest with free price, must call this function via the API.
# Note: When creating this contest, 
# the prize amount must be deposited into the contract before the contest ends.
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

# This function is called after the competition ends and distributes the prizes as follows:
#  30% for the first place, 20% for the second place, and 10% for the first place.
def Awardwinners(address_1 , address_2 , address_3 , ID ):
    address_1 = address_node.to_checksum_address(address_1)
    address_2 = address_node.to_checksum_address(address_2)
    address_3 = address_node.to_checksum_address(address_3)
    tx = contract.functions.Awardwinners(address_1 , address_2 , address_3 , int(ID) ).build_transaction({
        'from':owner_address ,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce_owner
    })
    sign_tx = w3.eth.account.sign_transaction(tx , PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(sign_tx.rawTransaction)
    return w3.to_hex(tx_hash)

# This function is called after the competition ends and divides 
# the prizes between the top 3 people according to the selected percentages.
def AwardWithPercentage(address_1 , address_2 , address_3 ,percent_1 , percent_2 , percent_3 , ID ):
    address_1 = address_node.to_checksum_address(address_1)
    address_2 = address_node.to_checksum_address(address_2)
    address_3 = address_node.to_checksum_address(address_3)
    tx = contract.functions.AwardWithPercentage(address_1 , address_2 , address_3 ,int(percent_1) , int(percent_2) , int(percent_3) , int(ID) ).build_transaction({
        'from':owner_address ,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce_owner
    })
    sign_tx = w3.eth.account.sign_transaction(tx , PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(sign_tx.rawTransaction)
    return w3.to_hex(tx_hash)

# This function is called after a two-player duel and gives the prize to the winner.
def Awardforduel_comp(address_1 , ID ):
    address_1 = address_node.to_checksum_address(address_1)
    tx = contract.functions.Awardforduel_comp(address_1 , int(ID) ).build_transaction({
        'from':owner_address ,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce_owner
    })
    sign_tx = w3.eth.account.sign_transaction(tx , PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(sign_tx.rawTransaction)
    return w3.to_hex(tx_hash)

# This function is called after free tournaments and sends prizes based on the amount of Ethereum, 
# for example 1 Ethereum for first place, 0.5 for second place, and .03 for third place. 
# The values will be taken as input.
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

# This function can be called for all competitions, 
# but it is recommended to use it only for competitions with 3 or more people due to the high fees.
#  It takes the prizes in the form of the amount of Ethereum and the address of each person and sends them to the Ethereum addresses.
#  This function can handle any number of prize winners.
def Awardforarbitrary_comp(winners_array , prize_array , ID):
    for i in range(len(prize_array)) :
        prize_array[i] = address_node.to_wei(prize_array[i] , 'ether')
    for j in range(len(winners_array)) :
        winners_array[j] = address_node.to_checksum_address(winners_array[j])
    tx = contract.functions.Awardforarbitrary_comp(winners_array , prize_array , int(ID)).build_transaction({
        'from':owner_address ,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce_owner

    })
    sign_tx = w3.eth.account.sign_transaction(tx , PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(sign_tx.rawTransaction)
    return w3.to_hex(tx_hash)

# This function will send the remaining Ethereum, which is the site's share of the competition,
#  to the relevant wallet after the competition prizes have been distributed.
def withdrawOwner(address , ID):
    address = address_node.to_checksum_address(address)
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