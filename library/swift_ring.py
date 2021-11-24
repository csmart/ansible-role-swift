#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2021 Chris Smart <distroguy@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from swift.common.ring import RingBuilder
from swift.common.ring.utils import parse_builder_ring_filename_args
from os.path import isfile

# sudo dnf -y install liberasurecode-devel
# python3 -m pip install swift

DOCUMENTATION = r"""
---
module: swift_ring

short_description: Manage OpenStack Swift rings

description: >
    This module can be used to create, modify and manage OpenStack Swift rings.
    This includes their creation and management such as setting replication,
    zones and regions along with adding and managing devices as well as
    validation and rebalance.

notes:
    - This module will require liberasurecode (such as `liberasurecode-devel`) and swift

author:
    - Chris Smart (@csmart) <distroguy@gmail.com>

options:
    name:
        description:
          - Name of the ring, e.g. account, container, object, object-1
          - Additional rings should have a dash plus number, e.g. object-1
        required: True
        type: str
    path:
        description: Path to the ring
        required: False
        type: str
        default: /etc/swift
    backup:
        description: Backup the ring and builder file
        required: False
        type: boolean
        default: False
    state:
        description: Whether the ring should exist or not
        required: False
        type: str
        default: present
    part_power:
        description: Partition power of the ring, required for new ring
        required: False
        type: int
    replicas:
        description: Number of replicas, required for new ring
        required: False
        type: float
    min_part_hours:
        description: Minimum hours between partition changes
        required: False
        type: int
        default: 1
    validate:
        description: Whether to validate the ring
        required: False
        type: boolean
        default: True
    rebalance:
        description: Whether to try and rebalance the ring
        required: False
        type: boolean
        default: True
    devices:
        description:
          - Devices for the ring as dict of dicts
          - The device dict's key is the id number of the device, must be unique
          - The device dict must include the following required keys: [ device, ip, port, region, weight, zone ]
          - The device dict may include the following optional keys: [ meta ]
        type: dict
        suboptions:
            <int>:
                type: dict
                description: Dict containing device details, key is unique disk id
            suboptions:
                device:
                    type: str
                    description: Full path to device, e.g. /dev/sdb
                ip:
                    type: str
                    description: IP address of the host for this device
                meta:
                    type: str
                    description: Metadata for this device
                port:
                    type: int
                    description: Port the service for this disk listens on
                region:
                    type: int
                    description: The region this device is located in
                state:
                    type: str
                    description: Whether the device should be in the ring, defaults to True
                weight:
                    type: int
                    description: The weight of this device for this ring
                zone:
                    type: int
                    description: The zone this device is located in
"""

EXAMPLES = r"""
- name: Create initial object ring
  swift_ring:
    name: object
    part_power: 17
    replicas: 3
    devices:
      0:
        device: "/dev/sdb"
        ip: "127.0.0.1"
        port: 8080
        region: 1
        weight: 100.0
        zone: 1
      1:
        device: "/dev/sdb"
        ip: "127.0.0.2"
        port: 8080
        region: 1
        weight: 100.0
        zone: 1
      2:
        device: "/dev/sdb"
        ip: "127.0.0.3"
        port: 8080
        region: 1
        weight: 100.0
        zone: 1
"""

RETURN = r"""
ring_info:
    description: Information about the ring, type, path, replicas, etc
    type: dict
    returned: always
    sample: {
            "backups": {
                'builder': 'object.builder.3212830.2022-09-04@21:42:05~',
                'ring': 'object.ring.gz.3212830.2022-09-04@21:42:05~'
                },
            "builder_file": "object.builder",
            "changed": [
                "replicas, device_added"
                ],
            "devs": [
                {
                    "device": "sdb",
                    "id": 0,
                    "ip": "127.0.0.1",
                    "meta": "/dev/sdb",
                    "parts": 0,
                    "port": 8080,
                    "region": 1,
                    "replication_ip": "127.0.0.1",
                    "replication_port": 8080,
                    "weight": 100.0,
                    "zone": 1
                },
                {
                    "device": "sdb",
                    "id": 1,
                    "ip": "127.0.0.2",
                    "meta": "/dev/sdb",
                    "parts": 0,
                    "port": 8080,
                    "region": 1,
                    "replication_ip": "127.0.0.2",
                    "replication_port": 8080,
                    "weight": 100.0,
                    "zone": 1
                },
                {
                    "device": "sdb",
                    "id": 2,
                    "ip": "127.0.0.3",
                    "meta": "/dev/sdb",
                    "parts": 0,
                    "port": 8080,
                    "region": 1,
                    "replication_ip": "127.0.0.3",
                    "replication_port": 8080,
                    "weight": 100.0,
                    "zone": 1
                }
                ],
            "min_part_hours": 1,
            "part_power": 17,
            "rebalanced": true,
            "replicas": 3.0,
            "ring_file": "object.ring.gz",
            "validated": true
        }
"""


def run_module():
    # Define supported arguments
    module_args = dict(
        backup=dict(type="bool", default="False"),
        create=dict(type="bool", default="True"),
        devices=dict(type="dict", default={}),
        min_part_hours=dict(type="int"),
        name=dict(type="str", required=True),
        part_power=dict(type="int", required=False),
        path=dict(type="path", default="/etc/swift/"),
        rebalance=dict(type="bool", default=True),
        replicas=dict(type="float", required=False),
        state=dict(
            type="str", default="present", choices=["absent", "present"]
        ),
        validate=dict(type="bool", default="True"),
    )

    # Instantiate Ansible module
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    # Seed result dict, fill in later as required
    result = dict(changed=False, original_message=module.params, message="")

    # Track existing devices so we know what is changed
    devs_in_current_ring = []

    params = module.params
    backup = params["backup"]
    create = params["create"]
    devices = params["devices"]
    min_part_hours = params["min_part_hours"]
    name = params["name"]
    part_power = params["part_power"]
    path = params["path"]
    rebalance = params["rebalance"]
    replicas = params["replicas"]
    state = params["state"]
    validate = params["validate"]

    if name.endswith("-0") or name.endswith("_0"):
        name = name[:-2]

    # Set results to return
    result["original_message"] = module.params

    result["message"] = {
        "backups": {},
        "changed": [],
        "rebalanced": False,
        "validated": False,
    }

    if not path.endswith("/"):
        path = path + "/"

    # Critical ring checks
    if part_power is not None and part_power > 32:
        module.fail_json(
            msg="Partition power of %d is greater than max of 32"
            % (part_power),
            **result
        )
        module.exit_json(**result)

    if replicas is not None and replicas < 1:
        module.fail_json(
            msg="Replicas of %d is invalid, must be at least 1" % (replicas),
            **result
        )
        module.exit_json(**result)

    if min_part_hours is not None and min_part_hours < 0:
        module.fail_json(
            msg="Min part hours of %d is invalid, cannot be \
                         negative"
            % (min_part_hours),
            **result
        )
        module.exit_json(**result)

    # Return if check mode
    if module.check_mode:
        module.exit_json(**result)

    # Do ring stuff here
    builder_file, ring_file = parse_builder_ring_filename_args(("", name))
    ring_file = path + ring_file
    builder_file = path + builder_file + ".builder"
    result["message"]["ring_file"] = ring_file
    result["message"]["builder_file"] = builder_file

    # TODO move this into functions
    # Load ring if exists, else create new ring
    if isfile(builder_file):
        # loading exiting ring
        try:
            ringbuilder = RingBuilder.load(builder_file)
        except Exception as e:
            module.fail_json(
                msg="Cannot open ring at: %s" % (builder_file), **result
            )
            module.exit_json(**result)
    else:
        # creating new ring
        if replicas is None:
            module.fail_json(
                msg="Ring does not exist and replicas not specified: %s"
                % (builder_file),
                **result
            )
            module.exit_json(**result)
        if part_power is None:
            module.fail_json(
                msg="Ring does not exist and part_power not specified: %s"
                % (builder_file),
                **result
            )
            module.exit_json(**result)
        if create:
            if min_part_hours is None:
                min_part_hours = 1
            ringbuilder = RingBuilder(part_power, replicas, min_part_hours)
            result["changed"] = True
            result["message"]["changed"].append("ring_created")
        else:
            module.fail_json(
                msg="Ring does not exist and create is set to \
                             false: %s"
                % (builder_file),
                **result
            )
            module.exit_json(**result)

    # Validations
    # Check part_power
    if part_power is not None and ringbuilder.part_power != part_power:
        module.fail_json(
            msg="Cannot change partition power without a ring \
                         rebuild: %s"
            % (builder_file),
            **result
        )
        module.exit_json(**result)

    result["message"]["part_power"] = ringbuilder.part_power

    # Ensure replicas and min_part_hours match args
    if replicas is not None and ringbuilder.replicas != replicas:
        ringbuilder.set_replicas(replicas)
        result["message"]["changed"].append("replicas")
        result["changed"] = True

    result["message"]["replicas"] = ringbuilder.replicas

    if (
        min_part_hours is not None
        and ringbuilder.min_part_hours != min_part_hours
    ):
        ringbuilder.change_min_part_hours(min_part_hours)
        result["message"]["changed"].append("min_part_hours")
        result["changed"] = True

    result["message"]["min_part_hours"] = ringbuilder.min_part_hours

    # Manage devices in the ring
    if devices:
        required_keys = (
            "device",
            "id",
            "ip",
            "port",
            "region",
            "weight",
            "zone",
        )
        optional_keys = (
            "meta",
            "replication_ip",
            "replication_port",
        )
        int_keys = ("region", "zone", "port", "replication_port")
        float_keys = "weight"
        dict_keys = "rings"
        missing_keys = ""
        for device, value in devices.items():
            # Make sure we have rings for this device
            if "rings" not in value:
                module.fail_json(
                    msg="No rings specified for device %s" % (device), **result
                )
                module.exit_json(**result)

            # Ansible devices doesn't have an ID, but Swift ring structure wants one
            value["id"] = int(device)

            # try and add/update the device in the ring
            for ring, value2 in value["rings"].items():
                # do nothing if this device is not in the current ring
                if name != ring:
                    continue

                # re-cast all elements in the dict
                # ansible seems to send some as strings
                for k, v in value.items():
                    if k in int_keys and not isinstance(v, int):
                        value[k] = int(v)
                    if k in float_keys and not isinstance(v, float):
                        value[k] = float(v)
                    if k in dict_keys and not isinstance(v, dict):
                        module.fail_json(
                            msg="Rings for device %s is not a dict" % (device),
                            **result
                        )
                        module.exit_json(**result)
                for k, v in value2.items():
                    if k in int_keys and not isinstance(v, int):
                        value[k] = int(v)
                    if k in float_keys and not isinstance(v, float):
                        value[k] = float(v)

                # build device
                # checks we have required keys at device or device.rings level
                device_dict = {}
                for key in required_keys:
                    try:
                        device_dict[key] = value2[key]
                    except:
                        try:
                            device_dict[key] = value[key]
                        except:
                            missing_keys = missing_keys + key + " "
                if missing_keys:
                    module.fail_json(
                        msg="Device missing required key(s): %s"
                        % (missing_keys),
                        **result
                    )
                    module.exit_json(**result)

                for key in optional_keys:
                    try:
                        device_dict[key] = value2[key]
                    except:
                        try:
                            device_dict[key] = value[key]
                        except:
                            pass

                # check if device is already in the ring
                existing_dev = None
                try:
                    existing_dev = ringbuilder.devs[value["id"]]
                except:
                    pass
                if existing_dev is None:
                    # add dev to the ring
                    try:
                        ringbuilder.add_dev(device_dict)
                        result["changed"] = True
                        result["message"]["changed"].append("device_added")
                    except:
                        module.fail_json(
                            msg="Could not add host to ring builder: %s"
                            % (builder_file),
                            **result
                        )
                        module.exit_json(**result)
                else:
                    # update dev in ring
                    # Store current device config for later and diff mode
                    devs_in_current_ring.append(existing_dev)
                    # Update the device values
                    for k, v in device_dict.items():
                        if ringbuilder.devs[value["id"]][k] != v:
                            try:
                                ringbuilder.devs[value["id"]][k] = v
                                result["changed"] = True
                                result["message"]["changed"].append(
                                    "device_changed"
                                )
                            except:
                                module.fail_json(
                                    msg="Could not update existing device in ring: %s"
                                    % (missing_keys),
                                    **result
                                )
                                module.exit_json(**result)

    # extract existing devices from ring
    result["message"]["devs"] = ringbuilder.devs

    # rebalance ring (cannot be empty)
    # TODO: when changed and weight not zero for all devs
    # if rebalance and ringbuilder.devs
    # and len(ringbuilder.devs) > ringbuilder.replicas:
    if rebalance and ringbuilder.devs and result["changed"] == True:
        try:
            ringbuilder.rebalance()
            result["message"]["rebalanced"] = True
            result["changed"] = True
            result["message"]["changed"].append("rebalanced")
        except:
            module.fail_json(
                msg="Could not rebalance the ring: %s" % (ring_file), **result
            )
            module.exit_json(**result)

    # revalidate
    # if validate and ringbuilder.devs
    # and len(ringbuilder.devs) > ringbuilder.replicas:
    if validate and ringbuilder.devs and result["changed"] == True:
        try:
            ringbuilder.validate()
            result["message"]["validated"] = True
            result["changed"] = True
        except:
            module.fail_json(
                msg="Could not validate ring: %s" % (builder_file), **result
            )
            module.exit_json(**result)

    # get ring from builder
    if result["changed"] == True:
        try:
            ring = ringbuilder.get_ring()
        except:
            module.fail_json(
                msg="Could not get ring from builder: %s" % (ring_file),
                **result
            )
            module.exit_json(**result)

    # if we got this far, then we have an updated and balanced ring
    # so we can write to disk

    # backup builder
    if backup and isfile(builder_file) and result["changed"] == True:
        try:
            backupdest = module.backup_local(builder_file)
            result["message"]["backups"]["builder"] = backupdest
        except:
            module.fail_json(
                msg="Could not create backup of builder file: %s"
                % (builder_file),
                **result
            )
            module.exit_json(**result)

    # write builder to disk
    if result["changed"] == True and not module.check_mode:
        try:
            ringbuilder.save(builder_file)
        except:
            module.fail_json(
                msg="Could not write ring builder file: %s" % (builder_file),
                **result
            )
            module.exit_json(**result)

    # backup ring
    if (
        backup
        and isfile(ring_file)
        and result["changed"] == True
        and not module.check_mode
    ):
        try:
            backupdest = module.backup_local(ring_file)
            result["message"]["backups"]["ring"] = backupdest
        except:
            module.fail_json(
                msg="Could not create backup of ring file: %s"
                % (builder_file),
                **result
            )
            module.exit_json(**result)

    # write ring to disk
    if result["changed"] == True and not module.check_mode:
        try:
            ring.save(ring_file)
        except:
            module.fail_json(
                msg="Could not write ring file: %s" % (ring_file), **result
            )
            module.exit_json(**result)

    # return results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
