const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("[Deploy] Deploying DeepShieldNotary contract...");

  const [deployer] = await hre.ethers.getSigners();
  console.log(`[Deploy] Using account: ${deployer.address}`);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log(`[Deploy] Account balance: ${hre.ethers.formatEther(balance)} ETH`);

  const DeepShieldNotary = await hre.ethers.getContractFactory("DeepShieldNotary");
  const contract = await DeepShieldNotary.deploy();
  await contract.waitForDeployment();

  const contractAddress = await contract.getAddress();
  console.log(`[Deploy] Contract deployed at: ${contractAddress}`);

  const outputPath = path.join(__dirname, "..", "deployed_address.txt");
  fs.writeFileSync(outputPath, contractAddress, "utf8");
  console.log(`[Deploy] Address saved to: ${outputPath}`);

  const artifact = await hre.artifacts.readArtifact("DeepShieldNotary");
  const abiPath = path.join(__dirname, "..", "contract_abi.json");
  fs.writeFileSync(abiPath, JSON.stringify(artifact.abi, null, 2), "utf8");
  console.log(`[Deploy] ABI saved to: ${abiPath}`);

  console.log("[Deploy] Done.");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("[Deploy] Error:", error);
    process.exit(1);
  });
