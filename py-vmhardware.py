"""
Python program that generates information about a Virtual Machine's vNICs and hard disks
"""

from __future__ import print_function
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl, vim
from datetime import datetime

import argparse
import atexit
import getpass


# Alter this to change the number of days for aged snapshots to display a warning in the output
warning_age = 7


def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(description='Process args for retrieving all the Virtual Machines')
    parser.add_argument('-s', '--host', required=True, action='store', help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store', help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store', help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=False, action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-m', '--vm', required=True, action='store', help='On eor more Virtual Machines to report on')
    args = parser.parse_args()
    return args


def get_properties(content, viewType, props, specType):
    # Build a view and get basic properties for all Virtual Machines
    """
    Obtains a list of specific properties for a particular Managed Object Reference data object.

    :param content: ServiceInstance Managed Object
    :param viewType: Type of Managed Object Reference that should populate the View
    :param props: A list of properties that should be retrieved for the entity
    :param specType: Type of Managed Object Reference that should be used for the Property Specification
    """
    objView = content.viewManager.CreateContainerView(content.rootFolder, viewType, True)
    tSpec = vim.PropertyCollector.TraversalSpec(name='tSpecName', path='view', skip=False, type=vim.view.ContainerView)
    pSpec = vim.PropertyCollector.PropertySpec(all=False, pathSet=props, type=specType)
    oSpec = vim.PropertyCollector.ObjectSpec(obj=objView, selectSet=[tSpec], skip=False)
    pfSpec = vim.PropertyCollector.FilterSpec(objectSet=[oSpec], propSet=[pSpec], reportMissingObjectsInResults=False)
    retOptions = vim.PropertyCollector.RetrieveOptions()
    totalProps = []
    retProps = content.propertyCollector.RetrievePropertiesEx(specSet=[pfSpec], options=retOptions)
    totalProps += retProps.objects
    while retProps.token:
        retProps = content.propertyCollector.ContinueRetrievePropertiesEx(token=retProps.token)
        totalProps += retProps.objects
    objView.Destroy()
    # Turn the output in retProps into a usable dictionary of values
    gpOutput = []
    for eachProp in totalProps:
        propDic = {}
        for prop in eachProp.propSet:
            propDic[prop.name] = prop.val
        propDic['moref'] = eachProp.obj
        gpOutput.append(propDic)
    return gpOutput


def print_vm_hardware(vm):
    disk_list = []
    network_list = []
    vm_hardware = vm.config.hardware
    vm_summary = vm.summary
    for each_vm_hardware in vm_hardware.device:
        if (each_vm_hardware.key >= 2000) and (each_vm_hardware.key < 3000):
            disk_list.append('{} | {:.1f}GB | {} | Thin: {}'.format(each_vm_hardware.deviceInfo.label,
                                                         each_vm_hardware.capacityInKB/1024/1024,
                                                         each_vm_hardware.backing.fileName,
                                                         each_vm_hardware.backing.thinProvisioned))
        elif (each_vm_hardware.key >= 4000) and (each_vm_hardware.key < 5000):
            network_list.append('{} | {} | {}'.format(each_vm_hardware.deviceInfo.label,
                                                         each_vm_hardware.deviceInfo.summary,
                                                         each_vm_hardware.macAddress))

    print('VM .vmx Path                   :', vm_summary.config.vmPathName)
    print('Virtual Disks                  :', disk_list[0])
    if len(disk_list) > 1:
        disk_list.pop(0)
        for each_disk in disk_list:
            print('                                ', each_disk)
    print('Virtual NIC(s)                 :', network_list[0])
    if len(network_list) > 1:
        network_list.pop(0)
        for each_vnic in network_list:
            print('                                ', each_vnic)

def main():
    args = GetArgs()
    try:
        vmnames = args.vm
        si = None
        if args.password:
            password = args.password
        else:
            password = getpass.getpass(prompt="Enter password for host {} and user {}: ".format(args.host, args.user))
        try:
            si = SmartConnect(host=args.host,
                              user=args.user,
                              pwd=password,
                              port=int(args.port))
        except IOError as e:
            pass
        if not si:
            print('Could not connect to the specified host using specified username and password')
            return -1

        atexit.register(Disconnect, si)
        content = si.RetrieveContent()

        retProps = get_properties(content, [vim.VirtualMachine], ['name', 'network'], vim.VirtualMachine)

        #Find VM supplied as arg and use Managed Object Reference (moref) for the PrintVmInfo
        for vm in retProps:
            if (vm['name'] in vmnames):
                print_vm_hardware(vm['moref'])
            elif vm['name'] in vmnames:
                print('ERROR: Problem connecting to Virtual Machine.  {} is likely powered off or suspended'.format(vm['name']))


    except vmodl.MethodFault as e:
        print('Caught vmodl fault : ' + e.msg)
        return -1
    except Exception as e:
        print('Caught exception : ' + str(e))
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
