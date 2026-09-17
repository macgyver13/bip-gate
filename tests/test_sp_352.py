"""Tests for BIP352 silent payment address structural lane."""

from __future__ import annotations

from bip_gate.lanes.sp_352 import Sp352Lane
from bip_gate.lanes.sp_address import (
    bech32m_encode,
    convertbits,
    decode_silent_payment_address,
    encode_silent_payment_address,
)
from bip_gate.schema import Claim, ClaimArtifacts

# Public BIP352 send_and_receive_test_vectors.json — no private keys
VECTOR_ADDR = (
    "sp1qqgste7k9hx0qftg6qmwlkqtwuy6cycyavzmzj85c6qdfhjdpdjtdgqjuexzk6murw56suy3e0rd2cgqvycxttddwsvgxe2usfpxumr70xc9pkqwv"
)
VECTOR_SCAN = "0220bcfac5b99e04ad1a06ddfb016ee13582609d60b6291e98d01a9bc9a16c96d4"
VECTOR_SPEND = "025cc9856d6f8375350e123978daac200c260cb5b5ae83106cab90484dcd8fcf36"

lane = Sp352Lane()


def test_lane_meta_partial():
    assert lane.meta.id == "sp_352"
    assert lane.meta.bip == 352
    assert lane.meta.status == "partial"


def test_valid_bip352_vector_address_pass():
    claim = Claim(
        summary="Receiver published a BIP352 silent payment address",
        artifacts=ClaimArtifacts(extra={"sp_address": VECTOR_ADDR}),
        asserted_bips=[352],
    )
    result = lane.check(claim)
    assert result.status == "pass"
    assert "structural" in result.evidence.lower() or "bech32m" in result.evidence.lower()


def test_valid_address_in_summary_regex():
    claim = Claim(
        summary=f"Please send to {VECTOR_ADDR} thanks",
        asserted_bips=[352],
    )
    result = lane.check(claim)
    assert result.status == "pass"


def test_invalid_checksum_fails():
    bad = VECTOR_ADDR[:-1] + ("w" if VECTOR_ADDR[-1] != "w" else "v")
    claim = Claim(
        summary="bad checksum address",
        artifacts=ClaimArtifacts(extra={"sp_address": bad}),
        asserted_bips=[352],
    )
    result = lane.check(claim)
    assert result.status == "fail"
    assert "checksum" in result.evidence.lower() or "invalid" in result.evidence.lower()


def test_bad_length_fails():
    short = bytes.fromhex(VECTOR_SCAN)  # 33 bytes only
    prog = convertbits(short, 8, 5, pad=True)
    assert prog is not None
    bad = bech32m_encode("sp", [0] + prog)
    claim = Claim(
        summary="wrong payload length",
        artifacts=ClaimArtifacts(extra={"sp_address": bad}),
        asserted_bips=[352],
    )
    result = lane.check(claim)
    assert result.status == "fail"
    assert "66" in result.evidence


def test_scan_spend_mismatch_fails():
    claim = Claim(
        summary="keys do not match address",
        artifacts=ClaimArtifacts(
            extra={
                "sp_address": VECTOR_ADDR,
                "scan_pub_key": VECTOR_SCAN,
                "spend_pub_key": VECTOR_SPEND[:-1]
                + ("0" if VECTOR_SPEND[-1] != "0" else "1"),
            }
        ),
        asserted_bips=[352],
    )
    result = lane.check(claim)
    assert result.status == "fail"
    assert "match" in result.evidence.lower()


def test_address_plus_matching_keys_pass():
    claim = Claim(
        summary="address with matching scan/spend pubs",
        artifacts=ClaimArtifacts(
            extra={
                "sp_address": VECTOR_ADDR,
                "scan_pub_key": VECTOR_SCAN,
                "spend_pub_key": VECTOR_SPEND,
            }
        ),
        asserted_bips=[352],
    )
    result = lane.check(claim)
    assert result.status == "pass"
    assert "match" in result.evidence.lower()


def test_no_artifact_need_human():
    claim = Claim(summary="We support BIP352", asserted_bips=[352])
    result = lane.check(claim)
    assert result.status == "need_human"


def test_protocol_math_claim_need_human():
    claim = Claim(
        summary="ECDH shared secret and output derivation completed for silent payments",
        artifacts=ClaimArtifacts(extra={"sp_address": VECTOR_ADDR}),
        asserted_bips=[352],
        claimed_complete=True,
    )
    result = lane.check(claim)
    assert result.status == "need_human"
    low = result.evidence.lower()
    assert "ecdh" in low or "not wired" in low or "protocol math" in low


def test_asserts_protocol_math_flag_need_human():
    claim = Claim(
        summary="structural address only narrative",
        artifacts=ClaimArtifacts(
            extra={
                "sp_address": VECTOR_ADDR,
                "asserts_protocol_math": True,
            }
        ),
        asserted_bips=[352],
        claimed_complete=False,
    )
    result = lane.check(claim)
    assert result.status == "need_human"


def test_decode_helper_vector():
    sp = decode_silent_payment_address(VECTOR_ADDR)
    assert sp.hrp == "sp"
    assert sp.version == 0
    assert sp.scan_pubkey.hex() == VECTOR_SCAN
    assert sp.spend_pubkey.hex() == VECTOR_SPEND
    assert encode_silent_payment_address(sp.scan_pubkey, sp.spend_pubkey) == VECTOR_ADDR


def test_bad_hrp_fails():
    claim = Claim(
        summary="wrong hrp",
        artifacts=ClaimArtifacts(
            extra={"sp_address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"}
        ),
        asserted_bips=[352],
    )
    result = lane.check(claim)
    assert result.status == "fail"


def test_addresses_list_extra():
    claim = Claim(
        summary="list form",
        artifacts=ClaimArtifacts(extra={"addresses": [VECTOR_ADDR]}),
        asserted_bips=[352],
    )
    assert lane.check(claim).status == "pass"
