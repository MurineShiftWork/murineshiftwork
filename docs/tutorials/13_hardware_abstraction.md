# Tutorial 13: Hardware abstraction *(optional)*

## Prerequisites

[Tutorial 12: Post-processing](12_post_processing.md). This page is for
developers adding a new device type.

## What you'll learn

- The four-method contract every device must satisfy.
- How devices are opened, handed to a task, and closed.
- The shape of adding a new device type.

## 1. Why an abstraction layer

A task asks for a capability ("I need a Bpod"), not a specific connection. The
hardware layer turns that request into a real, opened device and hands the task
only a handle. This is what lets the same task run on any rig: the rig's setup
file says where the device is, the hardware layer connects it, and the task never
sees a port string. Adding a new kind of device means satisfying one small
contract, with no changes to task code.

## 2. The device contract

Every device implements the same structural interface, `DeviceProtocol`. It has a
`name` attribute and four methods:

| Member | Responsibility |
|---|---|
| `name` | the key the device is exposed under (for example `"bpod"`) |
| `preflight()` | check the device is reachable before connecting; raise a clear error if not |
| `connect()` | open the hardware connection (with retries as appropriate) |
| `disconnect()` | close the connection gracefully |
| `handle` | the raw object handed to the task (a property) |

The split between `preflight` and `connect` is deliberate: preflight catches
"the device is not there" with a readable message before any connection state is
created, so failures are clean.

## 3. How devices are wired in

The `HardwareManager` takes a list of devices and manages their lifecycle as a
context manager. For each device it calls `preflight()`, then `connect()`, and on
exit calls `disconnect()` in reverse order. It returns a dict mapping each
device's `name` to its `handle`:

```python
from murineshiftwork.hardware.manager import HardwareManager

with HardwareManager([BpodDevice(port)]) as devices:
    # devices == {"bpod": <raw Bpod handle>}
    run_task(bpod=devices["bpod"], ...)
# disconnect() has now run for every opened device
```

The task receives only `devices["bpod"]`, the raw handle, and is unaware of the
device class or its port.

## 4. Adding a new device type (shape)

To support a new device, the work is:

1. Write a class that satisfies `DeviceProtocol`: set `name`, and implement
   `preflight`, `connect`, `disconnect`, and the `handle` property.
2. Construct it from the rig's setup config (the device's `type` and port live in
   the setup YAML under `devices`).
3. Include it in the list passed to `HardwareManager` for tasks that require it.

Because the contract is small and structural, a new device participates in
preflight, connection, and cleanup automatically once it implements the four
members. No task or framework code needs to know the new type by name.

## You now know

Every device satisfies a four-member `DeviceProtocol` (`name`, `preflight`,
`connect`, `disconnect`, `handle`), and `HardwareManager` opens, hands off, and
closes devices uniformly. Adding a device type means implementing that contract
and constructing it from the setup config, with no changes to task code.

## Next

[Tutorial 14: Valve calibration](14_calibration.md) *(optional)*. For how devices
fit the wider system, see [Architecture](../concepts/architecture.md).
