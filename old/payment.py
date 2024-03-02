from web3 import Web3, EthereumTesterProvider
import json
import os
from dotenv import load_dotenv

load_dotenv()
# Contract address and ABI
contract_address = "0xe281C0cEd3BE10189FD171287cd0Fe90E271eE01"
with open('abi.json', 'r') as abi_definition:
    contract_abi = json.load(abi_definition)

private_key = os.environ.get('WALLET_PRIVATE_KEY')
infura_api_key = os.environ.get('INFURA_API_KEY')
infura_project_id = os.environ.get('INFURA_PROJECT_ID')
# Instantiate the provider
w3 = Web3(Web3.HTTPProvider(f'https://goerli.infura.io/v3/{infura_api_key}'))

# Check if connected
print(w3.isConnected())  # Should print: "True"

# Create contract instance
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Accounts
from_account = '0xd91286B8421E6A46A845488579EF90Dfa313a65f'
to_account = '0x61c74fB5407F81835e4C14887b42DBC83C694eD7'

decimals = 9
# Number of tokens to send
tokens = 1000

# Convert to smallest unit (like Wei for Ether)
amount = tokens * 10**decimals

# Construct the transaction
transaction = contract.functions.transfer(to_account, amount).buildTransaction({
    'from': from_account,
    'nonce': w3.eth.getTransactionCount(from_account),
    'gas': 2000000,
    'gasPrice': w3.eth.gasPrice,
})
# Sign the transaction
signed_txn = w3.eth.account.signTransaction(transaction, private_key)

# Send the transaction
txn_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)

# Wait for the transaction to be mined, and get the transaction receipt
txn_receipt = w3.eth.waitForTransactionReceipt(txn_hash)

# Extract the transaction hash from the receipt
txn_hash = txn_receipt['transactionHash'].hex()

# Form a URL to view the transaction on Goerli Etherscan
url = f"https://goerli.etherscan.io/tx/{txn_hash}"


token_symbol = contract.functions.symbol().call()
print(f"Token Symbol: {token_symbol}")
print(url)
