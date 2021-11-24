# Deps

```bash
sudo dnf -y install liberasurecode-devel
python3 -m pip install swift
```

## Test with Python

```bash
python3 ./swift_ring.py test/test-swift-ring.json
```

## Test with Ansible

```bash
export ANSIBLE_LIBRARY=${PWD}
ansible-playbook -i test/inventory.yml test/test-swift-ring-inventory.yml
```
## Clean rings

```bash
./test/clean.sh
```

## TODO

- delete devs (if missing, or only if "state: absent"?)
- devices should use the default zone and region of ring?
