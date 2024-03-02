// Initialization of web3 and creating the contract instance
window.addEventListener('load', async () => {
    if (window.ethereum) {
        window.web3 = new Web3(ethereum);
        try {
            // Request account access if needed
            await ethereum.request({ method: 'eth_requestAccounts' });
            // After granting access, set up the contract instance
            window.contract = new web3.eth.Contract(contractABI, contractAddress);
        } catch (error) {
            console.error("User denied account access");
        }
    } else {
        console.log('Non-Ethereum browser detected. You should consider trying MetaMask!');
    }
});

async function transferTokens() {
    const amount = document.getElementById('amount').value; // The token amount the user wants to transfer
    const decimals = 9; // Your token's decimals
    const accounts = await web3.eth.getAccounts();
    const fromAccount = accounts[0];

    // Adjusting the amount for the token's decimals
    const amountInTokenBaseUnit = web3.utils.toBN(amount).mul(web3.utils.toBN(10).pow(web3.utils.toBN(decimals)));

    // Initiating the token transfer
    let transfer = contract.methods.transfer(recipientAddress, amountInTokenBaseUnit).send({ from: fromAccount });

    let confirmationListener = function(confirmationNumber, receipt){
        console.log("Transaction confirmed: ", confirmationNumber);

        // Stop listening after the third confirmation
        if (confirmationNumber >= 3) {
            console.log("Transaction has 3 confirmations");
            console.log("Receipt: ", receipt);
            console.log("Transaction hash: ", receipt.transactionHash);
            console.log("From account: ", fromAccount);
            console.log("Amount transferred: ", amountInTokenBaseUnit.toString());
            // Notify the backend after the third confirmation
            notifyBackend(receipt.transactionHash, fromAccount, amountInTokenBaseUnit.toString());

            transfer.off('confirmation', confirmationListener);
        }
    };

    transfer.on('transactionHash', function(hash){
        console.log("Transaction hash: " + hash);
    })
    .on('confirmation', confirmationListener)
    .on('receipt', function(receipt){
        console.log("Receipt: ", receipt);
    })
    .on('error', console.error);  // Log or handle errors appropriately
}

// Function to notify the backend about the initiated transaction
async function notifyBackend(txHash, fromAccount, amount) {
    const response = await fetch('/notify', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            tx_hash: txHash,
            from_account: [fromAccount],
            amounts: [amount], // assuming amount is a string
        }),
    });

    const responseData = await response.json();
    console.log(responseData);
}
