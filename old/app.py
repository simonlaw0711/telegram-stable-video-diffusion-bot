from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from web3 import Web3
from fastapi.middleware.cors import CORSMiddleware
from models.notify_request import NotifyRequest
import os
import json
import logging
from dotenv import load_dotenv
from old.database import DatabaseHandler

logger = logging.getLogger(__name__)
load_dotenv() 

app = Flask(__name__)
CORS(app)
db_handler = DatabaseHandler()

# Setup Web3
infura_api_key = os.environ.get('INFURA_API_KEY')
w3 = Web3(Web3.HTTPProvider(f'https://goerli.infura.io/v3/{infura_api_key}'))
print(w3.isConnected()) 

# Wallet for collect token
wallet_address = os.getenv("WALLET_ADDRESS")

# Your contract details
with open('abi.json', 'r') as abi_definition:
    contract_abi = json.load(abi_definition)
contract_address = os.getenv("CONTRACT_ADDRESS")
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Credits dictionary
credits = {}

@app.on_event("startup")
async def startup_event():
    await db_handler.connect_to_db()

@app.on_event("shutdown")
async def shutdown_event():
    await db_handler.disconnect_from_db()

@app.route("/")
def get_home():
    contract_address = os.getenv("CONTRACT_ADDRESS")
    with open('abi.json', 'r') as abi_definition:
        contract_abi = json.load(abi_definition)
    wallet_address = os.getenv("WALLET_ADDRESS")
    return render_template("index.html", contract_address=contract_address,
                           contract_abi=json.dumps(contract_abi),
                           wallet_address=wallet_address)

@app.post("/notify")
async def notify(request: NotifyRequest):
    try:
        receipt = w3.eth.getTransactionReceipt(request.tx_hash)
        toAccount = w3.toChecksumAddress(wallet_address)
        if not receipt:
            raise HTTPException(status_code=404, detail="Transaction receipt not found.")

        transfer_events = contract.events.Transfer().processReceipt(receipt)
        if not transfer_events:
            raise HTTPException(status_code=400, detail="No Transfer events found in the transaction.")

        # Validate each expected transfer against the found Transfer events
        for from_account, amount in zip(request.from_account, request.amounts):
            # Normalize addresses
            from_account = from_account.lower()
            match = False
            for event in transfer_events:
                event_args = event['args']
                if event_args['from'].lower() == from_account and \
                   event_args['to'].lower() == toAccount.lower() and \
                   str(event_args['value']) == amount:
                    match = True
                    break  # Stop checking if we've found a match for this transfer
            if not match:
                raise HTTPException(status_code=400, detail=f"Transfer from {from_account} for amount {amount} not found.")
            else:
                try:
                    success = await db_handler.update_user_credits("username_from_request", 8888)
                    if success:
                        return {"success": True, "message": "User record updated successfully."}
                    else:
                        return {"success": False, "message": "User not found."}
                except Exception as e:
                    raise HTTPException(status_code=500, detail=str(e))

        return {"success": True, "message": "All specified transfers verified successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))