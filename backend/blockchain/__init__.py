"""
blockchain/__init__.py

Anchors forensic report hashes on the local Hardhat blockchain.
The local node and contract are managed by blockchain/node_manager.py.
This module only handles individual transaction submission.
"""

from web3 import Web3

from blockchain import node_manager
from core.logger import get_logger

logger = get_logger(__name__)

# Contract ABI - must match DeepShieldNotary.sol exactly
NOTARY_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "reportHash", "type": "bytes32"},
            {"internalType": "string", "name": "analysisId", "type": "string"},
        ],
        "name": "anchorReport",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "reportHash", "type": "bytes32"}
        ],
        "name": "verifyReport",
        "outputs": [
            {
                "components": [
                    {"internalType": "string", "name": "analysisId", "type": "string"},
                    {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                    {"internalType": "address", "name": "anchoredBy", "type": "address"},
                    {"internalType": "bool", "name": "exists", "type": "bool"},
                ],
                "internalType": "struct DeepShieldNotary.Anchor",
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "bytes32",
                "name": "reportHash",
                "type": "bytes32",
            },
            {
                "indexed": False,
                "internalType": "string",
                "name": "analysisId",
                "type": "string",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "timestamp",
                "type": "uint256",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "anchoredBy",
                "type": "address",
            },
        ],
        "name": "ReportAnchored",
        "type": "event",
    },
]


def verify_on_chain(report_hash: str, analysis_id: str = "") -> dict:
    """
    Anchor a report hash on the local DeepShield blockchain.

    Args:
        report_hash: SHA-256 hex string of the forensic PDF report
        analysis_id: The DeepShield analysis UUID

    Returns:
        dict with transaction_hash, block_number, verification_url, status
        OR dict with 'error' key if something fails
    """
    if not node_manager.is_ready():
        logger.warning("[Blockchain] Node not ready - skipping anchoring")
        return {"error": "blockchain_not_ready"}

    contract_address = node_manager.get_contract_address()
    if not contract_address:
        logger.error("[Blockchain] No contract address available")
        return {"error": "contract_not_deployed"}

    try:
        rpc_url = node_manager.get_rpc_url()
        chain_id = node_manager.get_chain_id()
        private_key = node_manager.get_private_key()

        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            logger.error("[Blockchain] Cannot connect to local node")
            return {"error": "chain_unavailable"}

        account = w3.eth.account.from_key(private_key)

        clean_hash = report_hash.replace("0x", "").zfill(64)
        hash_bytes = bytes.fromhex(clean_hash)

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=NOTARY_ABI,
        )

        nonce = w3.eth.get_transaction_count(account.address)
        gas_estimate = contract.functions.anchorReport(
            hash_bytes, analysis_id
        ).estimate_gas({"from": account.address})
        gas_limit = int(gas_estimate * 1.2)
        gas_price = w3.eth.gas_price

        tx = contract.functions.anchorReport(hash_bytes, analysis_id).build_transaction(
            {
                "chainId": chain_id,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "nonce": nonce,
                "from": account.address,
            }
        )

        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        raw_transaction = getattr(signed_tx, "raw_transaction", None)
        if raw_transaction is None:
            raw_transaction = signed_tx.rawTransaction

        tx_hash = w3.eth.send_raw_transaction(raw_transaction)
        tx_hash_hex = Web3.to_hex(tx_hash)

        logger.info(f"[Blockchain] TX sent: {tx_hash_hex}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)

        if receipt.status == 1:
            block_number = receipt.blockNumber
            verification_url = f"http://127.0.0.1:8545/tx/{tx_hash_hex}"

            logger.info(
                f"[Blockchain] Anchored! Block: {block_number} | "
                f"TX: {tx_hash_hex[:20]}..."
            )

            return {
                "transaction_hash": tx_hash_hex,
                "block_number": block_number,
                "verification_url": verification_url,
                "status": "confirmed",
                "chain": "DeepShield Private Chain (Hardhat)",
                "chain_id": chain_id,
                "contract": contract_address,
            }

        logger.error("[Blockchain] Transaction reverted on-chain")
        return {"error": "transaction_reverted"}

    except Exception as e:
        logger.error(f"[Blockchain] Error during anchoring: {str(e)}", exc_info=True)
        return {"error": "chain_unavailable", "detail": str(e)}
