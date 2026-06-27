# OCPP Happy Path Transcript

This is the scenario the simulator sends for the happy-path charging session. The backend endpoint is:

```text
ws://backend:8000/ocpp/BER-001
```

# Boot

```json
[2,"boot-001","BootNotification",{"chargePointVendor":"Qwello","chargePointModel":"Demo"}]
```

Expected response:

```json
[3,"boot-001",{"currentTime":"<server-time>","interval":300,"status":"Accepted"}]
```

# Heartbeat

```json
[2,"heartbeat-001","Heartbeat",{}]
```

Expected response:

```json
[3,"heartbeat-001",{"currentTime":"<server-time>"}]
```

# Connector Available

```json
[2,"status-available-001","StatusNotification",{"connectorId":1,"status":"Available","errorCode":"NoError"}]
```

Expected response:

```json
[3,"status-available-001",{}]
```

# Authorize

```json
[2,"authorize-001","Authorize",{"idTag":"DEMO-TAG"}]
```

Expected response:

```json
[3,"authorize-001",{"idTagInfo":{"status":"Accepted"}}]
```

# Start Transaction

```json
[2,"start-001","StartTransaction",{"connectorId":1,"idTag":"DEMO-TAG","meterStart":12345,"transactionId":9001}]
```

Expected response:

```json
[3,"start-001",{"transactionId":<deterministic-demo-id>}]
```

# Meter Value

```json
[2,"meter-001","MeterValues",{"transactionId":9001,"connectorId":1,"meterValue":[{"timestamp":"2026-06-26T12:05:00Z","sampledValue":[{"value":"12410.5","unit":"kWh","measurand":"Energy.Active.Import.Register"}]}]}]
```

Expected response:

```json
[3,"meter-001",{}]
```

# Stop Transaction

```json
[2,"stop-001","StopTransaction",{"transactionId":9001,"meterStop":12410,"reason":"Local"}]
```

Expected response:

```json
[3,"stop-001",{}]
```

# Expected Backend State

- Station is online.
- Connector returns to `available`.
- Session is `completed`.
- Transaction is `closed`.
- One meter value is recorded.
- Every inbound frame has a raw OCPP message row.
- Every inbound frame has an outbox event for asynchronous processing.
