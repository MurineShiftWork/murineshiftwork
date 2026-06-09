# TODOs & Issues of RCE

- [ ] post session hooks for MSW/RCE
  - check TTL count and synch between msw-bpod == rce for each RPi
  - send MSW session data to `LabWatch`
- [ ] update MSW namespace for datetime + short hash
```
import hashlib

def short_hash(base: str, length: int = 6) -> str:
    """First `length` hex chars of SHA256 of the string."""
    return hashlib.sha256(base.encode()).hexdigest()[:length]


# Example usage:
basename = "t004_acute_m1102390_177__20260226_135958__probabilistic_switching_fixedsubjects".split("__")[0]
deterministic_id = short_hash(basename)
print(deterministic_id)  # e.g. "a1b2c3"
```

- [ ] add RCE data loader from dir (detect data model in dir to choose which loader to use)
