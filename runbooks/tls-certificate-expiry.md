---
category: cert_expiry
title: TLS certificate expiry
---
# TLS certificate expiry

## Symptoms
"x509: certificate has expired or is not yet valid", "tls: bad certificate" or handshake failures between two services or with a partner. Failures start abruptly, often at a round time such as midnight UTC, and affect every request on that connection.

## Likely causes
A server or client (mTLS) certificate reached its notAfter date; automated renewal failed or was never set up; a renewed certificate was issued but not reloaded by the process.

## Checks
Inspect the presented certificate's notAfter with openssl s_client. Check the renewal job or cert-manager Certificate status. Confirm which side (client or server) holds the expired certificate.

## Mitigation (human decision)
Issue and deploy a renewed certificate and restart or reload the consumer. Coordinate with the partner if their trust store needs updating. Add expiry alerts well ahead of notAfter.
