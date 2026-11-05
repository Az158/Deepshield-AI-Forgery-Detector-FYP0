// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DeepShieldNotary
 * @notice Stores SHA-256 hashes of forensic PDF reports on-chain.
 *         Once a hash is anchored, it cannot be changed or deleted.
 *         This provides tamper-evident proof that a specific report existed
 *         at a specific point in time.
 */
contract DeepShieldNotary {

    struct Anchor {
        string analysisId;    // DeepShield analysis UUID
        uint256 timestamp;    // Block timestamp when anchored
        address anchoredBy;   // Wallet that submitted the hash
        bool exists;          // Whether this hash has been anchored
    }

    // Maps report hash (bytes32) to its anchor record
    mapping(bytes32 => Anchor) public anchors;

    // Emitted every time a new hash is anchored
    event ReportAnchored(
        bytes32 indexed reportHash,
        string analysisId,
        uint256 timestamp,
        address indexed anchoredBy
    );

    /**
     * @notice Anchor a report hash on-chain.
     * @param reportHash SHA-256 hash of the forensic PDF, as bytes32
     * @param analysisId The DeepShield analysis UUID for reference
     */
    function anchorReport(bytes32 reportHash, string calldata analysisId) external {
        require(reportHash != bytes32(0), "DeepShield: hash cannot be zero");
        require(!anchors[reportHash].exists, "DeepShield: hash already anchored");

        anchors[reportHash] = Anchor({
            analysisId: analysisId,
            timestamp: block.timestamp,
            anchoredBy: msg.sender,
            exists: true
        });

        emit ReportAnchored(reportHash, analysisId, block.timestamp, msg.sender);
    }

    /**
     * @notice Look up an anchored record by its report hash.
     * @param reportHash SHA-256 hash of the PDF report
     * @return The Anchor struct, or a zeroed struct if not found
     */
    function verifyReport(bytes32 reportHash) external view returns (Anchor memory) {
        return anchors[reportHash];
    }
}
