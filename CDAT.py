#!/usr/bin/python
#-*-coding:utf-8-*-
'''
Filename: CDAT.py
Version: Python 3.7.2
Authors: Aaron Warner (aawarner@cisco.com)
         Wade Lehrschall (wlehrsch@cisco.com)
         Kris Swanson (kriswans@cisco.com)
Description:    This program will perform API calls to automate the deployment and deletion of NFVIS VNF's and virtual
                switches. The program is currently interactive only. The program also has a "demo reset" option which
                will decommission SDWAN routers in Cisco vManage, delete ENCS from Cisco DNA Center inventory, and
                delete VNF's and virtual switches from NFVIS.
'''

from Cisco_NFV_API_SDK import NFVIS_API_Calls as nfvis_calls
from Cisco_NFV_API_SDK import NFVIS_URNs as nfvis_urns
from Cisco_NFV_API_SDK import SDWAN_API_Calls as sdwan_calls
from Cisco_NFV_API_SDK import SDWAN_URNs as sdwan_urns
from pprint import pprint as pp
from os import listdir
import json
import sys
import requests
import getpass
from tabulate import tabulate
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def getcreds():
    # Collects NFVIS IP Address, Username, and Password
    nfvis = input("What is the IP address of the NFVIS system: ")
    url = "https://" + nfvis
    print("Enter your username and password. ")
    username = input("Username: ")
    password = getpass.getpass()
    return nfvis, url, username, password


def response_parser(response_json):
    o=response_json
    print(60*'#'+'\n\n''Hierarchical Config:\n')
    try:
        for i in o.keys():
            print(i)
            j=o[i]
            try:
                for k in j.keys():
                    print('\t|\n\t-->%s'%k)
                    l=o[i][k]
                    for m in l:
                        if type(m)==type({}):
                            for n in m.keys():
                                try:
                                    if type(m[n])==type({}):
                                        for a in (m[n]).keys():
                                            print('\t\t\t\t|\n\t\t\t\t-->%s'%(m[n][a]))
                                except:
                                    pass
                                try:
                                    if type(m[n])==type(''):
                                        print('\t\t|\n\t\t-->%s'%m[n])
                                except:
                                    pass
                                try:
                                    if type(m[n])==type([]):
                                        for b in m[n]:
                                            for c in b.keys():
                                                print('\t\t\t|\n\t\t\t-->%s'%b[c])
                                except:
                                    pass
                        if type(l)==type({}):
                            print('\t\t|\n\t\t-->%s:%s'%(m,l[m]))
                        if type(m)==type([]):
                            for d in m:
                                print('\t\t|\n\t\t-->%s'%d)
            except:
                pass
    except:
        pass


def cli(args):
    if len(sys.argv)==5:
        method,key,name_ip,setting=(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4])
    else:
        method,key,name_ip=(sys.argv[1],sys.argv[2],sys.argv[3])
    if 'creds.json' not in listdir():
        username = input("Username: ")
        password = getpass.getpass()
        creds={name_ip:{username:password}}
        with open('creds.json','w') as f:
            json.dump(creds,f)
    with open ('creds.json','r') as f:
        creds=json.load(f)

    if name_ip not in creds.keys():
        username = input("Username: ")
        password = getpass.getpass()
        creds.update({name_ip:{username:password}})
        with open('creds.json','w') as f:
            json.dump(creds,f)
    else:
        username,password=(list(creds[name_ip].keys())[0],list(creds[name_ip].values())[0])

    url='https://%s'%name_ip
    if method is 'g':
        uri,header=nfvis_urns.get(key,url)
        code,response_json=nfvis_calls.get(username,password,uri,header)
        print("API Response Code: %i :\n\nRequest URI: %s\n\nJSON Reponse:\n\n%s\n\n"%(code,uri,response_json))
        response_parser(response_json)
    if method is 'p':
        uri,header,post_data=nfvis_urns.post(key,url,format='xml')
        with open(setting) as f:
            contents=f.read()
        code,response=nfvis_calls.post(username,password,uri,header,xml_data=contents)
        print("API Response Code: %i :\n\nRequest URI: %s\n\nJSON Reponse:\n\n%s\n\n"%(code,uri,response))
    if method is 'd':
        uri,header=nfvis_urns.delete(key,url,vnf=setting,bridge=setting,network=setting)
        code,response=nfvis_calls.delete(username,password,uri,header)
        print('\n%s \nAPI Status Code: %i\n'%(uri,code))

def sdwan_reset(vmanage, vmanage_username, vmanage_password):
    # Collect vManage IP Address, Username, and Password and decommission SDWAN Routers
    url = "https://" + vmanage
    uri, header = sdwan_urns.get('vedges', url)
    code, response_json = sdwan_calls.get(vmanage_username, vmanage_password, uri, header)
    print("API Response Code: %i :\n%s" % (code, uri))
    if code == 401:
        print("Authentication Failed to Device")
        sys.exit()
    else:
        print("\nGetting list of SDWAN vEdge's from vManage: \n")
        table = []
        headers_dict = {"SDWAN UUID": 'uuid', " Device Model": 'deviceModel', "Host Name": 'host-name',
                        "Device IP": 'deviceIP', "Template": 'template'}
        headers = [i for i in headers_dict.keys()]
        for event in response_json["data"]:
            tr = []
            for i in headers:
                try:
                    tr.append(event[headers_dict[i]])
                except:
                    tr.append("N/A")
                    pass
            table.append(tr)
        print(tabulate(table, headers=headers, tablefmt="fancy_grid"))
        print()
    uuid = input("Enter the UUID of the SDWAN router you wish to decommission: ")
    print("Deccommissioning SDWAN Router...")
    uri, header = sdwan_urns.put("decommission", url, data=uuid)
    code, response = sdwan_calls.put(vmanage_username, vmanage_password, uri, header)
    print('\n%s \nAPI Status Code: %i\n' % (uri, code))
    if response.status_code != 200:
        print("SDWAN decommissioning failed\n")
    else:
        print("SDWAN decommissioning successful\n")

def nfvis_reset():
    # Delete running VNFs' from NFVIS
    nfvis, url, username, password = getcreds()
    print("Currently Deployed VNF's...")
    uri,header=nfvis_urns.get('deployments',url)
    code,response_json=nfvis_calls.get(username,password,uri,header)
    print("API Response Code: %i :\n%s"%(code,uri))
    if code == 401:
        print("\nAuthentication Failed to Device")
    else:
        print()
    try:
        for i in response_json["vmlc:deployments"]["deployment"]:
            print(i["name"]+'\n')
    except Exception as e:
        if code == 204:
            print("There are no running VNF deployments on device.\n")
            return
        else:
            print(repr(e))
    print()
    vnf = input("\nWhat VNF would you like to delete? ")
    uri,header=nfvis_urns.delete('vnf',url,vnf=vnf)
    code,response=nfvis_calls.delete(username,password,uri,header)
    print('\n%s \nAPI Status Code: %i\n'%(uri,code))
    if code != 204:
        print("VNF deletion failed")
    else:
        print("VNF deletion successful")

def dnac_reset():
    # Gather DNAC IP Address, Username, Password, and delete ENCS from inventory
    dnac = input("Enter the Cisco DNA Center IP address: \n")
    print("Enter the Username and Password for Cisco DNA Center: \n")
    dnac_username = input("Username: ")
    dnac_password = getpass.getpass()
    headers = {"content-type" : "application/json"}
    payload = {"isForceDelete" : "true"}
    response = requests.post("https://" + dnac + "/dna/system/api/v1/auth/token", verify=False,
                            auth=HTTPBasicAuth(dnac_username, dnac_password),
                            headers=headers)
    print("API Response Code: ", response.status_code)
    if response.status_code == 401:
        print("Authentication Failed to Device")
        sys.exit()
    else:
        token = response.json()["Token"]
    headers["x-auth-token"] = token
    response = requests.get("https://" + dnac + "/dna/intent/api/v1/network-device", headers=headers, verify=False)
    print()
    print("Getting list of Network Devices in inventory from DNA-C")
    print()
    data = response.json()
    for event in data["response"]:
        print("Hostname: ", event["hostname"], "with Device ID: ", event["id"])
    print()
    device_id = input("Enter the Device ID of the device you wish to delete: ")

    response = requests.delete("https://" + dnac + "/dna/intent/api/v1/network-device/" + device_id, params=payload, headers=headers, verify=False)
    if response.status_code != 202:
        print("Device deletion from inventory failed")
        print("API Response Code: ", response.status_code)
        print()
    else:
        print("Device deletion from inventory successful")
        print("API Response Code: ", response.status_code)
        print()

def deploy_bridge(nfvis, url, username, password):
    bridgedata = input("What is the name of data file for the bridge to be deployed?\n")
    contents = open(bridgedata).read()
    print(contents)
    uri,header,post_data=nfvis_urns.post('bridges',url,format='xml')
    code,response=nfvis_calls.post(username,password,uri,header,xml_data=contents)
    print('\n%s \nAPI Status Code: %i\n'%(uri,code))

    if code != 201:
        print("Bridge deployment failed\n")
    else:
        print("Bridge deployment successful\n")

def deploy_vnetwork(nfvis, url, username, password):
    networkdata = input("What is the name of data file for the network to be deployed?\n")
    contents = open(networkdata).read()
    print(contents)
    uri,header,post_data=nfvis_urns.post('networks',url,format='xml')
    code,response=nfvis_calls.post(username,password,uri,header,xml_data=contents)
    print('\n%s \nAPI Status Code: %i\n'%(uri,code))
    if code != 201:
        print("Network deployment failed\n")
    else:
        print("Network deployment successful\n")

def deploy_vnf(nfvis, url, username, password):
    vnfdata = input("What is the name of data file for the VNF to be deployed?\n")
    contents = open(vnfdata).read()
    print(contents)
    uri,header,post_data=nfvis_urns.post('deployments',url,format='xml')
    code,response=nfvis_calls.post(username,password,uri,header,xml_data=contents)
    print('\n%s \nAPI Status Code: %i\n'%(uri,code))
    if code != 201:
        print("VNF deployment failed\n")
    else:
        print("VNF deployment successful\n")

# Menu Options
def print_options():
    print("Select an option from the menu below. \n")
    print(" Options: \n")
    print(" '1' List NFVIS system information")
    print(" '2' List running VNF's from NFVIS")
    print(" '3' Delete Virtual Switch from NFVIS")
    print(" '4' Delete VNF from NFVIS")
    print(" '5' Deploy Virtual Switch to NFVIS from file")
    print(" '6' Deploy VNF to NFVIS from file")
    print(" '7' Deploy Service Chained VNFs to NFVIS")
    print(" '8' Reset demo environment")
    print(" 'p' print options")
    print(" 'q' quit the program")

def main():

    '''

    Program Entry Point
    '''

    print("#################################")
    print("####Cisco DNA Automation Tool####")
    print("################################# \n")

    choice = "p"
    while choice != "q":
        if choice == "1":
            # API call to retrieve system info, then displays it, return to options
            nfvis, url, username, password = getcreds()
            uri,header=nfvis_urns.get('platform-detail',url)
            code,response_json=nfvis_calls.get(username,password,uri,header)
            print("API Response Code: %i :\n%s"%(code,uri))
            if code == 401:
                print("Authentication Failed to Device \n")
            else:
                print("Platform Details: \n")
            try:
                print(tabulate([i for i in response_json['platform_info:platform-detail']['hardware_info'].items()],tablefmt="fancy_grid"))
            except Exception as e:
                print(repr(e))
            print_options()
            choice = input("Option: ")

        elif choice == "2":
            # API call to list running VNFs, display info, return to options
            nfvis, url, username, password = getcreds()
            uri,header=nfvis_urns.get('deployments',url)
            code,response_json=nfvis_calls.get(username,password,uri,header)
            print("API Response Code: %i :\n%s"%(code,uri))
            if code == 401:
                print("Authentication Failed to Device \n")
            else:
                print("Currently Deployed VNF's: \n")
            try:
                [print(i["name"]+'\n') for i in response_json["vmlc:deployments"]["deployment"]]
            except Exception as e:
                if code == 204:
                    print("There are no running VNF deployments on device. \n")
                else:
                    print(repr(e))
            print_options()
            choice = input("Option: ")

        elif choice == "3":
            # API call to display running bridges/networks. Then API call to delete bridge/network of choice

            nfvis, url, username, password = getcreds()

            uri,header=nfvis_urns.get('networks',url)
            code,response_json=nfvis_calls.get(username,password,uri,header)
            print("API Response Code: %i :\n%s"%(code,uri))

            if code == 401:
                print("Authentication Failed to Device")
                sys.exit()
            else:
                print("Currently Deployed Virtual Switches on NFVIS: \n")
            try:
                [print(i["name"]+'\n') for i in response_json["network:networks"]["network"]]
            except Exception as e:
                print(repr(e))
            print()
            print("NOTE:  Do not delete the lan-net, wan-net, wan2-net or SRIOV vswitches, these are system generated! \n")
            vswitch = input("Which Virtual Switch would you like to delete? ")
            uri,header=nfvis_urns.delete('network',url,network=vswitch)
            code,response=nfvis_calls.delete(username,password,uri,header)
            print("API Response Code: %i :\n%s"%(code,uri))

            if code != 204:
                print("Virtual Switch deletion failed \n")
            else:
                print("Virtual Switch deletion successful \n")
            # API call to get running bridges on NFVIS device

            uri,header=nfvis_urns.get('bridges',url)
            code,response_json=nfvis_calls.get(username,password,uri,header)
            print("API Response Code: %i :\n%s"%(code,uri))

            if code == 401:
                print("Authentication Failed to Device")
                sys.exit()
            else:
                print("Currently Deployed Virtual Bridges on NFVIS: \n")
            try:
                [print(i["name"]+'\n') for i in response_json["network:bridges"]["bridge"]]
            except Exception as e:
                print(repr(e))
            print()
            print("NOTE:  Do not delete the lan-br, wan-br, wan2-br or SRIOV vswitches, these are system generated! \n")
            bridge = input("Which Virtual Bridge would you like to delete? ")

            uri,header=nfvis_urns.delete('bridge',url,bridge=bridge)
            code,response=nfvis_calls.delete(username,password,uri,header)
            print("API Response Code: %i :\n%s"%(code,uri))

            if code != 204:
                print("Virtual Bridge deletion failed \n")
            else:
                print("Virtual Bridge deletion successful \n")
            print_options()
            choice = input("Option: ")

        elif choice == "4":
            # API call to display currently running VNF's then enter VNF to delete and API call to delete

            nfvis_reset()
            print_options()
            choice = input("Option: ")

        elif choice == "5":
            # API call to deploy bridges/networks to NFVIS

            nfvis, url, username, password = getcreds()
            deploy_bridge(nfvis, url, username, password)
            deploy_vnetwork(nfvis, url, username, password)
            print_options()
            choice = input("Option: ")

        elif choice == "6":
            # API call to deploy VNF to NFVIS

            nfvis, url, username, password = getcreds()
            deploy_vnf(nfvis, url, username, password)
            print_options()
            choice = input("Option: ")

        elif choice == "7":
            # API calls to deploy virtual networking and VNF's to NFVIS
            nfvis, url, username, password = getcreds()

            deploy_bridge(nfvis, url, username, password)
            answer = input("Would you like to deploy another bridge? (y or n) \n")
            while answer == ('y'):
                deploy_bridge(nfvis, url, username, password)
                answer = input("Would you like to deploy another bridge? (y or n) \n")
            else:
                print("Bridge deployment complete. Let's deploy the virtual network. \n")
            deploy_vnetwork(nfvis, url, username, password)
            answer = input("Would you like to deploy another virtual network? (y or n) \n")
            while answer == ('y'):
                deploy_vnetwork(nfvis, url, username, password)
                answer = input("Would you like to deploy another virtual network? (y or n) \n")
            else:
                print("Virtual network deployment complete. Let's deploy the virtual network functions. \n")
            deploy_vnf(nfvis, url, username, password)
            answer = input("Would you like to deploy another virtual network function? (y or n) \n")
            while answer == ('y'):
                deploy_vnf(nfvis, url, username, password)
                answer = input("Would you like to deploy another virtual network function? (y or n) \n")
            else:
                print("Virtual network function deployment complete.\n Service chain deployment complete. \n")
            print_options()
            choice = input("Option: ")

        elif choice == "8":
            # API calls to reset demo environment, print demo environment reset
            vmanage = input("Enter the vManage IP address: \n")
            print("Enter the Username and Password for vManage: \n")
            vmanage_username = input("Username: ")
            vmanage_password = getpass.getpass()
            sdwan_reset(vmanage, vmanage_username, vmanage_password)
            answer = input("Would you like to decommission another SDWAN router? (y or n) \n")
            while answer == ('y'):
                sdwan_reset(vmanage, vmanage_username, vmanage_password)
                answer = input("Would you like to decommission another SDWAN router? (y or n) \n")
            else:
                print("Great. Let's reset NFVIS. \n")
            nfvis_reset()
            answer = input("Would you like to decommission another NFVIS VNF? (y or n) \n")
            while answer == ('y'):
                nfvis_reset()
            else:
                print("Great. Let's reset Cisco DNA Center. \n")
            dnac_reset()
            answer = input("Would you like to delete another device from DNA-C inventory? (y or n) \n")
            while answer == ('y'):
                dnac_reset()
            else:
                print("Great. Demo Environment has been reset. \n")
            print_options()
            choice = input("Option: ")

        elif choice == "p":
            print_options()
            choice = input("Option: ")

        elif choice != "1" or "2" or "3" or "4" or "5" or "6" or "7" or "8" or "p" or "q":
            print("Wrong option was selected \n")
            sys.exit()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        main()
    else:
        cli(sys.argv)
