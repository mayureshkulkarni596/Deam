# Hardware protocol status

Phase 0 includes only a backend GateController interface and mock implementation. No serial protocol or Arduino sketch exists yet.

Phase 3 will define bounded OPEN commands, acknowledgements, sequence/replay handling, heartbeat/reconnect behavior, timeout semantics, and hardware-side automatic closing. Use mock mode only until that protocol is implemented and tested.
