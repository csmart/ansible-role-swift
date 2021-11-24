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

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from swift.common.ring import RingBuilder
from swift.common.ring.utils import parse_builder_ring_filename_args
from os.path import isfile

# sudo dnf -y install liberasurecode-devel
# python3 -m pip install swift

DOCUMENTATION = r'''
---
module: swift_ring

short_description: Manage OpenStack Swift rings

description: Create, modify and manage OpenStack Swift rings

options:
    type:
        description: Type of the ring, e.g. account, container, object
        required: true
        type: str
    id:
        description: The ID of the object policy, e.g. 0, 1, 2
        required: false
        type: int
        default: 0
    path:
        description: Path to the ring
        required: false
        type: str
        default: /etc/swift
    backup:
        description: Backup the ring and builder file
        required: false
        type: boolean
        default: False
    state:
        description: Whether the ring should exist or not
        required: false
        type: str
        default: present
    part_power:
        description: Partition power of the ring
        required: true
        type: int
    replicas:
        description: Number of replicas
        required: true
        type: float
    min_part_hours:
        description: Minimum hours between partition changes
        required: False
        type: int
        default: 1
    validate:
        description: Whether to validate the ring
        required: false
        type: boolean
        default: True
    rebalance:
        description: Whether to try and rebalance the ring
        required: false
        type: boolean
        default: True
author:
    - Chris Smart (@csmart)
'''

EXAMPLES = r'''
- name: Create initial object ring
  swift_ring:
    type: object
    part_power: 17
    replicas: 3
'''

RETURN = r'''
ring_info:
    description: Information about the ring, type, path, replicas, etc
    type: dict
    returned: always
    sample: {
            "backedup": false,
            "builder_file": "object.builder",
            "min_part_hours": 0,
            "part_power": 17,
            "rebalanced": false,
            "replicas": 3.0,
            "ring_file": "object.ring.gz",
            "validated": false
        }
'''


def run_module():
    # define supported arguments
    module_args = dict(
        backup=dict(type='bool', default='False'),
        create=dict(type='bool', default='True'),
        devices=dict(type='list', default=[]),
        min_part_hours=dict(type='int', default=1),
        type=dict(type='str', required=True),
        id=dict(type='int', required=False),
        part_power=dict(type='int', required=True),
        path=dict(type='path', default='/etc/swift/'),
        rebalance=dict(type='bool', default=True),
        replicas=dict(type='float', required=True),
        state=dict(type='str', default='present', choices=['absent',
                                                           'present']),
        validate=dict(type='bool', default='True')
    )

    # instantiate Ansible module
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # seed result dict, fill in later as required
    result = dict(
        changed=False,
        original_message=module.params,
        message=''
    )

    params = module.params
    backup = params['backup']
    create = params['create']
    devices = params['devices']
    min_part_hours = params['min_part_hours']
    type = params['type']
    id = params['id']
    part_power = params['part_power']
    path = params['path']
    rebalance = params['rebalance']
    replicas = params['replicas']
    state = params['state']
    validate = params['validate']

    if id and id != 0 and type == "object":
        type = type + '-' + str(id)

    # set results to return
    result['original_message'] = module.params

    result['message'] = {
        'backedup': False,
        'rebalanced': False,
        'validated':  False
    }

    if not path.endswith('/'):
        path = path + '/'

    # checks
    if part_power > 32:
        module.fail_json(msg='Partition power of %d is greater than max of 32'
                         % (part_power), **result)
        module.exit_json(**result)

    if replicas < 1:
        module.fail_json(msg='Replicas of %d is invalid, must be at least 1'
                         % (replicas), **result)
        module.exit_json(**result)

    if min_part_hours < 0:
        module.fail_json(msg='Min part hours of %d is invalid, cannot be \
                         negative' % (min_part_hours), **result)
        module.exit_json(**result)

    # return if check mode
    if module.check_mode:
        module.exit_json(**result)

    # do ring stuff here
    builder_file, ring_file = parse_builder_ring_filename_args(('', type))
    ring_file = path + ring_file
    builder_file = path + builder_file + '.builder'
    result['message']['ring_file'] = ring_file
    result['message']['builder_file'] = builder_file

    # TODO move this into functions
    # load ring if exists, else create new object
    if isfile(builder_file):
        # print('loading ring')
        try:
            ringbuilder = RingBuilder.load(builder_file)
        except Exception as e:
            module.fail_json(msg='Cannot open ring at: %s' % (builder_file),
                             **result)
            module.exit_json(**result)
    else:
        # print('creating new ring')
        if create:
            ringbuilder = RingBuilder(part_power, replicas, min_part_hours)
            result['changed'] = True
        else:
            module.fail_json(msg='Ring does not exist and create is set to \
                             false: %s' % (builder_file), **result)
            module.exit_json(**result)

    # print('have the ring devs changed')
    # print(ringbuilder.devs_changed)

    # validation
    # print('part_power: ' + str(ringbuilder.part_power))
    # print('\nreplicas: ' + str(ringbuilder.replicas))
    # print('min_part_hours: ' + str(ringbuilder.min_part_hours))

    # check part_power
    if ringbuilder.part_power != part_power:
        module.fail_json(msg='Cannot change partition power without a ring \
                         rebuild: %s' % (builder_file), **result)
        module.exit_json(**result)

    result['message']['part_power'] = ringbuilder.part_power

    # ensure replicas and min_part_hours match args
    if ringbuilder.replicas != replicas:
        ringbuilder.set_replicas(replicas)
        result['changed'] = True

    result['message']['replicas'] = ringbuilder.replicas

    if ringbuilder.min_part_hours != min_part_hours:
        ringbuilder.change_min_part_hours(min_part_hours)
        result['changed'] = True

    result['message']['min_part_hours'] = ringbuilder.min_part_hours

    # print('have the ring devs changed')
    # print(ringbuilder.devs_changed)

    # make changes as per inventory (add/remove disks)
    # should be a dict with the following
    #  - id
    #  - weight
    #  - region
    #  - zone
    #  - ip
    #  - port
    #  - replication_ip ?
    #  - replication_port?
    #  - device
    #  - meta

    if devices:
        required_keys = ('region', 'zone', 'ip', 'port', 'device', 'weight')
        int_keys = ('id', 'region', 'zone', 'port', 'replication_port')
        float_keys = ('weight')
        missing_keys = ''
        for dev in devices:
            # check that we have required keys
            for k in required_keys:
                if k not in dev:
                    missing_keys = missing_keys + k + " "
            if missing_keys:
                module.fail_json(msg='Device missing required key(s): %s' %
                                 (missing_keys), **result)
                module.exit_json(**result)
            # recast all elements in the dict
            # ansible seems to send some as strings
            for k, v in dev.items():
                if k in int_keys and not isinstance(v, int):
                    dev[k] = int(v)
                if k in float_keys and not isinstance(v, float):
                    dev[k] = float(v)
            # if we made it this far, let's try and add the device
            try:
                ringbuilder.add_dev(dev)
                result['changed'] = True
            except:
                module.fail_json(msg='Could not add host to ring builder: %s' %
                                 (builder_file), **result)
                module.exit_json(**result)

    # extract existing devices from ring
    # print("devs")
    # print(ringbuilder.devs)
    # print("devs end")
    result['message']['devs'] = ringbuilder.devs

    # rebalance ring (cannot be empty)
    # TODO: when changed and weight not zero for all devs
    # if rebalance and ringbuilder.devs
    # and len(ringbuilder.devs) > ringbuilder.replicas:
    if rebalance and ringbuilder.devs:
        try:
            ringbuilder.rebalance()
            result['message']['rebalanced'] = True
        except:
            module.fail_json(msg='Could not rebalance the ring: %s' %
                             (ring_file), **result)
            module.exit_json(**result)

    # revalidate
    # if validate and ringbuilder.devs
    # and len(ringbuilder.devs) > ringbuilder.replicas:
    if validate and ringbuilder.devs:
        try:
            ringbuilder.validate()
            result['message']['validated'] = True
        except:
            module.fail_json(msg='Could not validate ring: %s' %
                             (builder_file), **result)
            module.exit_json(**result)

    # get ring from builder
    try:
        ring = ringbuilder.get_ring()
    except:
        module.fail_json(msg='Could not get ring from builder: %s' %
                         (ring_file), **result)
        module.exit_json(**result)

    # if we got this far, then we have an updated and balanced ring
    # so we can write to disk

    # backup builder
    if backup and isfile(builder_file):
        try:
            backupdest = module.backup_local(builder_file)
            result['message']['backedup'] = True
        except:
            module.fail_json(msg='Could not create backup of builder file: %s'
                             % (builder_file), **result)
            module.exit_json(**result)

    # write builder to disk
    try:
        ringbuilder.save(builder_file)
    except:
        module.fail_json(msg='Could not write ring builder file: %s' %
                         (builder_file), **result)
        module.exit_json(**result)

    # backup ring
    if backup and isfile(ring_file):
        try:
            backupdest = module.backup_local(ring_file)
            result['message']['backedup'] = True
        except:
            module.fail_json(msg='Could not create backup of ring file: %s' %
                             (builder_file), **result)
            module.exit_json(**result)

    # write ring to disk
    try:
        ring.save(ring_file)
    except:
        module.fail_json(msg='Could not write ring file: %s' % (ring_file),
                         **result)
        module.exit_json(**result)

    # update results object as neccesary

    # determine if changed
    # if module.params['name']:
    #    result['changed'] = True

    # determine if failed
    if module.params['type'] == 'null':
        module.fail_json(msg='Cannot open ring', **result)

    # return results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
