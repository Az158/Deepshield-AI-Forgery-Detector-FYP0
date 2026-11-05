"""
blockchain/node_manager.py

Manages the lifecycle of the local Hardhat blockchain node.
The node runs as a subprocess. This module starts it, waits for it
to be ready, deploys the smart contract, and provides the RPC URL
and contract address to the rest of the application.
"""

import shutil
import subprocess
import threading
import time
from pathlib import Path

from web3 import Web3

from blockchain.contract_deployer import compile_contract, deploy_contract
from core.logger import get_logger

logger = get_logger(__name__)

# -- Paths -----------------------------------------------------------------
BLOCKCHAIN_DIR = Path(__file__).parent
HARDHAT_DIR = BLOCKCHAIN_DIR / "hardhat"

# -- Constants -------------------------------------------------------------
HARDHAT_RPC_URL = "http://127.0.0.1:8545"
HARDHAT_CHAIN_ID = 31337

# This is Hardhat's default account #0 - deterministic, always the same.
# It has 10000 ETH pre-loaded in the local node.
HARDHAT_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# -- State -----------------------------------------------------------------
_node_process: subprocess.Popen | None = None
_contract_address: str | None = None
_is_ready: bool = False


def _command(name: str) -> str:
    """Resolve Windows .cmd shims when PowerShell script execution is restricted."""
    if shutil.which(f"{name}.cmd"):
        return f"{name}.cmd"
    return name


def _stream_output(process: subprocess.Popen) -> None:
    """Read and log Hardhat node stdout in a background thread."""
    if process.stdout is None:
        return

    for line in iter(process.stdout.readline, b""):
        decoded = line.decode("utf-8", errors="replace").rstrip()
        if decoded:
            if "Error" in decoded or "error" in decoded or "EADDRINUSE" in decoded:
                logger.error(f"[Hardhat] {decoded}")
            elif "Started HTTP" in decoded:
                logger.info(f"[Hardhat] {decoded}")
            else:
                logger.debug(f"[Hardhat] {decoded}")


def _wait_for_node(timeout: int = 30) -> bool:
    """
    Poll the RPC endpoint until the node is ready or timeout expires.
    Returns True if ready, False if timed out.
    """
    w3 = Web3(Web3.HTTPProvider(HARDHAT_RPC_URL))
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if _node_process is not None and _node_process.poll() is not None:
                logger.error(
                    f"[Blockchain] Hardhat node exited early with code "
                    f"{_node_process.returncode}"
                )
                return False

            if w3.is_connected():
                # Require a few consecutive successful JSON-RPC calls. A TCP
                # listener can appear just before Hardhat is fully usable.
                for _ in range(3):
                    if _node_process is not None and _node_process.poll() is not None:
                        return False
                    _ = w3.eth.chain_id
                    time.sleep(0.5)
                logger.info("[Blockchain] Hardhat node is ready")
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _install_dependencies() -> bool:
    """Run npm install in the hardhat directory if node_modules is missing."""
    node_modules = HARDHAT_DIR / "node_modules"
    if node_modules.exists():
        logger.info("[Blockchain] npm dependencies already installed")
        return True

    logger.info("[Blockchain] Installing npm dependencies (first run - takes ~30s)...")
    try:
        result = subprocess.run(
            [_command("npm"), "install"],
            cwd=str(HARDHAT_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            logger.info("[Blockchain] npm install complete")
            return True

        logger.error(f"[Blockchain] npm install failed: {result.stderr}")
        return False
    except Exception as e:
        logger.error(f"[Blockchain] npm install error: {e}")
        return False


def start_blockchain() -> bool:
    """
    Start the local Hardhat blockchain node and deploy the contract.

    This is called once at FastAPI startup. Returns True if successful,
    False if anything fails. The rest of the application continues
    regardless - blockchain failure never blocks the detection pipeline.
    """
    global _node_process, _contract_address, _is_ready

    if _is_ready:
        return True

    logger.info("[Blockchain] Starting local Hardhat node...")

    if not _install_dependencies():
        logger.warning("[Blockchain] Dependency install failed - blockchain disabled")
        return False

    if not compile_contract():
        logger.warning("[Blockchain] Compilation failed - blockchain disabled")
        return False

    try:
        _node_process = subprocess.Popen(
            [_command("npx"), "hardhat", "node", "--port", "8545"],
            cwd=str(HARDHAT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        thread = threading.Thread(
            target=_stream_output,
            args=(_node_process,),
            daemon=True,
        )
        thread.start()

    except Exception as e:
        logger.error(f"[Blockchain] Failed to start node: {e}")
        return False

    if not _wait_for_node(timeout=30):
        logger.error("[Blockchain] Node did not become ready in time")
        stop_blockchain()
        return False

    if _node_process.poll() is not None:
        logger.error("[Blockchain] Hardhat node exited before deployment")
        stop_blockchain()
        return False

    time.sleep(2)

    if _node_process.poll() is not None:
        logger.error("[Blockchain] Hardhat node exited before deployment")
        stop_blockchain()
        return False

    address = deploy_contract()
    if not address:
        logger.error("[Blockchain] Contract deployment failed - blockchain disabled")
        stop_blockchain()
        return False

    _contract_address = address
    _is_ready = True

    logger.info("=" * 55)
    logger.info("[Blockchain] Local blockchain is LIVE")
    logger.info(f"[Blockchain] RPC:      {HARDHAT_RPC_URL}")
    logger.info(f"[Blockchain] Chain ID: {HARDHAT_CHAIN_ID}")
    logger.info(f"[Blockchain] Contract: {_contract_address}")
    logger.info("=" * 55)

    return True


def stop_blockchain() -> None:
    """Stop the Hardhat node. Called at FastAPI shutdown."""
    global _node_process, _is_ready

    if _node_process is not None:
        logger.info("[Blockchain] Stopping Hardhat node...")
        _node_process.terminate()
        try:
            _node_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _node_process.kill()
        _node_process = None

    _is_ready = False
    logger.info("[Blockchain] Node stopped")


def get_rpc_url() -> str:
    return HARDHAT_RPC_URL


def get_chain_id() -> int:
    return HARDHAT_CHAIN_ID


def get_private_key() -> str:
    return HARDHAT_PRIVATE_KEY


def get_contract_address() -> str | None:
    return _contract_address


def is_ready() -> bool:
    return _is_ready
