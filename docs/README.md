# PeerConnect source code documentation

## System Architecture

PeerConnect follows an IPC-style design for seamless integration with the User Interface (React.js).

[diagrams](<https://excalidraw.com/?#json=JwupHwQ7QuQyK1BEYFhdl,528_biXX7getTXAvT763uw>)

## Table of Contents

| module             |                 src                 |                  docs                  | desc                              |
|:-------------------|:-----------------------------------:|:--------------------------------------:|:----------------------------------|
| src.avails         |         [link](/src/avails)         |      [link](/docs/core/README.md)      | helpers, bases, utilites          |
| src.core           |          [link](/src/core)          |      [link](/docs/core/README.md)      | core application functionality    |
| src.managers       |        [link](/src/managers)        |    [link](/docs/managers/README.md)    | high level service APIs           |
| src.transfers      |       [link](/src/transfers)        |    [link](/docs/transfer/README.md)    | transfers files                   |
| src.conduit        |        [link](/src/conduit)         |    [link](/docs/conduit/README.md)     | communicating with User Interface |
| src.configurations |     [link](/src/configurations)     | [link](/docs/configurations/README.md) | start up configurations           |
| src.server         |         [link](/src/server)         |                  N/A                   | connecting to peer-connect servers|
| logging            | [link](/src/managers/logmanager.py) |    [link](/docs/logging/README.md)     | logging configurations            |

## Legend

| notation | meaning              |
|:--------:|:---------------------|
|   WIP    | work in progress     |
|   RIP    | refactor in progress |
|   DEP    | deprecated           |
|   TBD    | To Be Decided        |
