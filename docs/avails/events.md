# Event Types

Named tuple definitions for system events.

## Event Classes

1. **RequestEvent**
   - `root_code`: Operation type code
   - `request`: WireData payload
   - `from_addr`: Source address

2. **GossipEvent**
   - `message`: GossipMessage object
   - `from_addr`: Source address

3. **ConnectionEvent**
   - `connection`: Connection object
   - `handshake`: Initial WireData

4. **MessageEvent**
   - `msg`: Received WireData
   - `connection`: Source MsgConnection

## Purpose

Standardized event definitions for system communication.

[back](/docs/avails)
