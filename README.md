Swift
=====

This is a role for setting up and managing OpenStack Swift clusters.
Currently it supports PACO nodes running all Swift services; Proxy, Account, Container and Object.

It will:

 - Prepare Swift nodes, including setting SELinux and ensuring SSH access
 - Add repositories and install packages
 - Configure dependent services, such as logging, rsyncd and memcached
 - Configure keepalived for failover of proxy VIPs
 - Configure Swift PACO services
 - Create initial account, container and object rings
 - Prepare disks on each node, format and mount according to the rings
 - Build and distribute the rings
 - Configure dispersion
 - Simple operational tasks such as:
   - Update and distribute the rings
   - Re-configure PACO services
   - Generate dispersion and replication reports


Requirements
------------

An inventory of pre-existing CentOS 8 Stream nodes with their networking configured.
The cluster requires an admin box (included in `swift_admin` group) from which all the Swift nodes are managed.

If building a virtual Swift cluster, consider using `csmart.virt_infra` Ansible role at https://github.com/csmart/ansible-role-virt-infra.

Sample inventory and playbooks can be found at https://github.com/csmart/virt-infra-swift for both `csmart.virt_infra` and `csmart.swift`.


Role Variables
--------------

This role has a number of default variables, which are broken out into individual files under `defaults/main/`.
These include common settings for a Swift cluster, as well as defaults for specific Swift services.

 - account-rings.yml
 - account.yml
 - container-rings.yml
 - container.yml
 - dispersion.yml
 - hash.yml
 - networks.yml
 - object-rings.yml
 - object.yml
 - packages.yml
 - proxy.yml
 - swift.yml
 - tempauth.yml

Required global variables that the user must define, include:

 - `swift_hash_suffix` - the hash suffix of the cluster, once set it should not be changed
    - default is `07b4ef9c-2e01-4ea2-a109-5ffc5273225f`
 - `swift_hash_prefix` - the hash prefix of the cluster, once set it should not be changed
    - default is `f9175259-ace0-48bb-af9d-e7ac505b89d2`
 - `swift_outward_subnet` - the routable CIDR subnet for external connections (for proxy nodes)
   - default is `203.0.113.0/24`
 - `swift_cluster_subnet` - the cluster communication CIDR subnet
   - default is `192.0.2.0/24`
 - `swift_replication_subnet` - replication CIDR subnet (can be the same as cluster)
   - default is `198.51.100.0/24`

Required node specific variables that the user must define, include:

 - `swift_outward_ip` - IP on the outward network
   - for example, `203.0.113.11`
 - `swift_cluster_ip` - IP on the cluster network
   - for example, `192.0.2.11`
 - `swift_replication_ip` - IP on the replication network
   - for example, `198.51.100.11`
 - `swift_vips` - list of proxy VIPs, 4th octet of IP

    - Each proxy node should list the 4th octet of the VIP IP in order of preference. For example, based on default outward subnet of `203.0.113.0/24`, here's a node which wants VIPs `203.0.113.111`, `203.0.113.112` and `203.0.113.113`.

        ```yaml
        swift_vips:
          - 111
          - 112
          - 113
        ```

 - `swift_rings_disks` - list of dicts defining what disks to use for what ring
    - Each node's disks should include the path and what weight it should have for a ring. For example, here's a SCSI disk to be used for objects and an NVMe to be used for both acount and container.

        ```yaml
        swift_rings_disks:
          - disk:
              device: sdb
              rings:
              - name: account
                weight: 0
              - name: container
                weight: 0
              - name: object
                weight: 100
          - disk:
              device: nvme0n1
              rings:
              - name: account
                weight: 100
              - name: container
                weight: 100
              - name: object
                weight: 0
        ```


Dependencies
------------

None.

Example Playbook
----------------

The `virt-infra-swift` repository at https://github.com/csmart/virt-infra-swift provides a set of example playbooks and sample inventory.

Your inventory should include the following groups:

 - `swift` (or `all`)
 - `swift_admin`
 - `swift_proxy`
 - `swift_account`
 - `swift_container`
 - `swift_object`

Here is an example inventory for a three node PACO Swift cluster with required groups.

```yaml
swift:
  hosts:
    swift-admin:
    swift-[01:03]:
  children:
    swift_admin:
      hosts:
        swift-admin:
    swift_proxy:
      hosts:
        swift-[01:03]:
    swift_account:
      hosts:
        swift-[01:03]:
    swift_container:
      hosts:
        swift-[01:03]:
    swift_object:
      hosts:
        swift-[01:03]:
```

Once you have a basic inventory, creating a basic playbook should be simple.

```yaml
---
- hosts: swift
  tasks:
    - include_role:
        name: csmart.swift
```

Executing the playbook will run the whole role and default set of tasks, in order.

```bash
ansible-playbook -i inventory/ site.yml
```

The role also includes tags for each type of task, so you could create one or more playbooks for all or specific tags.

```yaml
---
- hosts: swift
  tasks:
    - include_role:
        name: csmart.swift
      tags:
        - account
        - common
        - config
        - container
        - disks
        - dispersion
        - hosts
        - keepalived
        - logging
        - memcached
        - object
        - packages
        - prep
        - proxy
        - rings
        - rsyncd
        - selinux
        - services
        - system
        - update
```

Then run the playbook against specific tags, for example, to just re-configure account services.

```bash
ansible-playbook -i inventory/ site.yml --tags account
```


License
-------

GPLv3+

Author Information
------------------

Chris Smart https://blog.christophersmart.com
