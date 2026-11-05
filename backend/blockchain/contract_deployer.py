"""
blockchain/contract_deployer.py

Compiles and deploys the DeepShieldNotary contract to the local Hardhat node.
"""

import shutil
import subprocess
import time
from pathlib import Path

from web3 import Web3

from core.logger import get_logger

logger = get_logger(__name__)

BLOCKCHAIN_DIR = Path(__file__).parent
HARDHAT_DIR = BLOCKCHAIN_DIR / "hardhat"
DEPLOYED_ADDRESS_FILE = HARDHAT_DIR / "deployed_address.txt"
HARDHAT_RPC_URL = "http://127.0.0.1:8545"


def _command(name: str) -> str:
    """Resolve Windows .cmd shims when PowerShell script execution is restricted."""
    if shutil.which(f"{name}.cmd"):
        return f"{name}.cmd"
    return name


def compile_contract() -> bool:
    """Compile the Solidity contract."""
    logger.info("[Blockchain] Compiling smart contract...")
    try:
        result = subprocess.run(
            [_command("npx"), "hardhat", "compile"],
            cwd=str(HARDHAT_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            logger.info("[Blockchain] Contract compiled successfully")
            return True

        logger.error(f"[Blockchain] Compilation failed: {result.stderr}")
        return False
    except Exception as e:
        logger.error(f"[Blockchain] Compilation error: {e}")
        return False


def deploy_contract() -> str | None:
    """
    Deploy the DeepShieldNotary contract to the local Hardhat node.
    Returns the deployed contract address, or None on failure.
    """
    logger.info("[Blockchain] Deploying DeepShieldNotary contract...")
    w3 = Web3(Web3.HTTPProvider(HARDHAT_RPC_URL))

    for attempt in range(1, 6):
        if not w3.is_connected():
            logger.warning(
                f"[Blockchain] RPC not ready before deploy attempt {attempt}/5"
            )
            time.sleep(1)
            continue

        try:
            result = subprocess.run(
                [
                    _command("npx"),
                    "hardhat",
                    "run",
                    "scripts/deploy.js",
                    "--network",
                    "localhost",
                ],
                cwd=str(HARDHAT_DIR),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.error(
                    "[Blockchain] Deployment attempt "
                    f"{attempt}/5 failed: {result.stderr or result.stdout}"
                )
                time.sleep(1)
                continue

            if DEPLOYED_ADDRESS_FILE.exists():
                address = DEPLOYED_ADDRESS_FILE.read_text().strip()
                logger.info(f"[Blockchain] Contract deployed at: {address}")
                return address

            logger.error("[Blockchain] deployed_address.txt not found after deploy")
            return None

        except Exception as e:
            logger.error(f"[Blockchain] Deployment attempt {attempt}/5 error: {e}")
            time.sleep(1)

    return None
