# Base Classes and Protocols

Core abstractions and interfaces used throughout the system.

## Key Components

### Protocols

- **HasID**: Protocol for objects with ID attribute
- **HasPeerId**: Protocol for objects with peer_id
- **HasIdProperty**: Protocol for objects with id property

### Handler System

**Note**: These exist as a mere reference that define what a handler is w.r.t [dispatchers](#dispatcher-system)
application code no longer use these classes, instead it uses closer function definitions

- `AbstractHandler`: Base handler interface
- `BaseHandler`: Concrete handler implementation
- `RequestHandler`: Specialized handler for request events

### Dispatcher System

- `AbstractDispatcher`: Event dispatching interface
- `BaseDispatcher`: Basic dispatcher implementation with registry

### Gossip Components

- `RumorMessageList`: Abstract base for rumor message storage
- `RumorPolicy`: Abstract base for rumor propagation policies

## Usage

Provides foundational types for event handling and message propagation patterns.

[back](/docs/avails)
