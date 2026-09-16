# BIP test vectors

This directory holds **placeholders** and pointers only. Do not commit private
keys or secrets. Pull public vectors from the BIPs themselves:

| Lane / BIP | Upstream vectors |
|------------|------------------|
| BIP174 (PSBT) | https://github.com/bitcoin/bips/blob/master/bip-0174.mediawiki#test-vectors |
| BIP370 (PSBTv2) | https://github.com/bitcoin/bips/blob/master/bip-0370.mediawiki |
| BIP352 (Silent Payments) | https://github.com/bitcoin/bips/blob/master/bip-0352.mediawiki#test-vectors |
| BIP375 (SP send / PSBT) | https://github.com/bitcoin/bips/blob/master/bip-0375.mediawiki#test-vectors — JSON at `bip-0375/bip375_test_vectors.json` |
| BIP376 (SP spend) | https://github.com/bitcoin/bips/blob/master/bip-0376.mediawiki (when available) |
| BIP392 (SP descriptors) | https://github.com/bitcoin/bips/blob/master/bip-0392.mediawiki (when available) |

When deepening a lane, vendor only the public fixture subset needed for
structural checks, and cite the BIP section in checker `refs`.
