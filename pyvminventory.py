#!/usr/bin/env python
#
# pyvminventory
#
# Author: Diego Mariani - dmariani (at) avantune.com
#

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

import os
import sys
import atexit
import ssl

import xml.etree.ElementTree as ET    # necessario per creazione file XML
from xml.dom import minidom    # necessario per creazione file XML

import paramiko
import socket    # per gestire le exception di paramiko

import warnings    # workaround per eliminare warning ad ogni connessione
warnings.filterwarnings(action='ignore',module='.*paramiko.*')    # workaround per eliminare warning ad ogni connessione

# Definizione percorsi files e directory necessari per l'esecuzione
# todo - utilizzare sys.path[0] o os.path.dirname(os.path.realpath(__file__)) invece dei percorsi assoluti
file_logins = "/opt/pyvminventory/logins.txt"    # esempio: /opt/pyvminventory/logins.txt
""" file_logins format
esx,hostname,username,password
lxc,hostname,username,password
"""

file_hostlist = "/opt/pyvminventory/web/hostlist.txt"    # esempio: /opt/pyvminventory/web/hostlist.txt
open(file_hostlist,"w").close()    # scrivo il file vuoto per non far fallire check_path_exists

dir_xml = "/opt/pyvminventory/web/xml/"    # esempio: /opt/pyvminventory/web/xml/

# Definizione funzione per check esistenza files e directory
def check_path_exists(*args):
# Se tutti i files e le directory esistono continuo l'esecuzione dello script, altrimenti esco
    for arg in args:
        if os.path.exists(arg) == True:
            pass
        else:
            sys.exit(str(arg) + ": No such file or directory")
    pass

# Esecuzione funzione check esistenza files e directory
check_path_exists(file_logins, file_hostlist, dir_xml)

# Definizione funzione per normalizzazione file file_logins e creazione lista
def norm_logins():
    with open (file_logins,"r") as f:
        return map(str.strip,f.readlines())    # strip \n alla fine di ogni elemento della lista

# Assegnazione lista ottenuta dalla manipolazione di file_logins
logins = norm_logins()

# Definizione funzione per connettersi ad un ESX che ritorna una lista nested che contiene tutte le vm ed i relativi dettagli
def connector_esx(host, user, pwd):
    # todo - mettere tutto sotto try except per gestire eventuali eccezioni
    context = None
    if hasattr(ssl, '_create_unverified_context'):
       context = ssl._create_unverified_context()

    si = SmartConnect(host=host, user=user, pwd=pwd, port=443, sslContext=context)
    # todo - gestire in maniera migliore l'errore utente e password sbagliati
    if not si:
        print("Could not connect to the specified host using specified "
              "username and password")

    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    vm_list = []    # lista nested contenente tutte le liste semplici vm_details
    for child in content.rootFolder.childEntity:
        if hasattr(child, 'vmFolder'):
            datacenter = child
            vmFolder = datacenter.vmFolder
            vmList = vmFolder.childEntity
            for vm in vmList:
                vm_details = []    # lista semplice contenente i dettagli della singola vm
                vmid = str(vm.summary.vm)
                vm_details.append(vmid[20:-1])    # vmid
                vm_details.append(str(vm.summary.config.name))    # name
                vm_details.append(str(vm.guest.ipAddress))    # ipaddress
                vm_details.append(str(vm.guest.hostName))    # hostname
                vm_details.append(str(vm.summary.config.guestFullName))    # guestos
                # se la descrizione è formattata correttamente la splitto utilizzando " - " come delimitatore
                if vm.summary.config.annotation and vm.summary.config.annotation.count(" - ") == 3:
                    annotation_split = vm.summary.config.annotation.split(" - ")
                # se la descrizione esiste ma non è formattata correttamente la inserisco completamente nel campo description
                elif vm.summary.config.annotation:
                    annotation_split = ["","",str(vm.summary.config.annotation),""]
                # se la descrizione non esiste imposto come vuoti i campi owner, team, description e expirydate
                else:
                    annotation_split = ["","","",""]
                vm_details.append(str(annotation_split[0]))    # owner
                vm_details.append(str(annotation_split[1]))    # team
                vm_details.append(str(annotation_split[2]))    # description
                expirydate = str(annotation_split[3]).replace("Scadenza:", "")
                vm_details.append(str.strip(expirydate))    # expirydate
                vm_list.append(vm_details)    # append della lista vm_details alla lista nested vm_list
    return vm_list

# todo - Definizione funzione per connettersi ad un LXC che ritorna una lista nested che contiene tutte le vm ed i relativi dettagli
def connector_lxc(host, user, pwd):
    try:
        vm_list = []    # lista nested contenente tutte le liste semplici vm_details
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy)

        client.connect(hostname=host, port=22, username=user, password=pwd, timeout=10)

        stdin, stdout, stderr = client.exec_command("lxc-ls")
        for line in stdout.readlines():
            vm_details = ["", "", "", "", "", "", "", "", ""]    # lista semplice contenente i dettagli della singola vm
            vm_details[1] = vm_details[3] = str.strip(line)    # name e hostname
            stdin, stdout, stderr = client.exec_command("lxc-info -n " + str.strip(line) + " -pH && lxc-info -n " + str.strip(line) + " -iH")
            details = stdout.readlines()
            if len(details) > 0:
                vm_details[0] = str.strip(details[0])    # vmid
                vm_details[2] = str.strip(details[1])    # ipaddress
            else:
                vm_details[0] = ""    # vmid
                vm_details[2] = ""    # ipdrress
            vm_list.append(vm_details)    # append della lista vm_details alla lista nested vm_list

    except socket.error:
        pass

    finally:
        client.close()
        return vm_list

# Definizione funzione che costruisce un file XML, prendendo in input l'output (liste nested) delle funzioni connector_esx e connector_lxc
def xml_constructor(host, args):
    xml_host = ET.Element("host")    # Definizione radice dell'albero XML
    i = 0
    while i < len(args):
        xml_vm = ET.SubElement(xml_host, "vm")    # vm
        ET.SubElement(xml_vm, "vmid").text = str(args[i][0])    # vmid
        ET.SubElement(xml_vm, "name").text = str(args[i][1])    # name
        ET.SubElement(xml_vm, "ipaddress").text = str(args[i][2])    # ipaddress
        ET.SubElement(xml_vm, "hostname").text = str(args[i][3])    # hostname
        ET.SubElement(xml_vm, "guestos").text = str(args[i][4])    # guestos
        ET.SubElement(xml_vm, "owner").text = str(args[i][5])    # owner
        ET.SubElement(xml_vm, "team").text = str(args[i][6])    # team
        ET.SubElement(xml_vm, "description").text = str(args[i][7])    # description
        ET.SubElement(xml_vm, "expirydate").text = str(args[i][8])    # expirydate
        i += 1
    xml_reparsed = minidom.parseString(ET.tostring(xml_host, encoding="utf-8"))    # Somma di tutti i nodi per costruzione albero XML
    xml_tree = xml_reparsed.toprettyxml(indent="  ", encoding="utf-8")    # Aggiunta prolog iniziale e indentazioni all'albero XML
    with open(dir_xml + host + ".xml", "wb") as f:
        f.write(xml_tree)

# Meccanismo che si occupa di indirizzare al giusto connettore a seconda del contenuto di file_logins (ESX o LXC)
for row in logins:
    hypervisor = row.split(",")[0]
    host = row.split(",")[1]
    user = row.split(",")[2]
    pwd = row.split(",")[3]
    if hypervisor == "esx":
        xml_constructor(host, connector_esx(host, user, pwd))
    elif hypervisor == "lxc":
        xml_constructor(host, connector_lxc(host, user, pwd))
    else:
        pass

# Assegnazione lista ottenuta dalla manipolazione di file_logins
logins = norm_logins()
# Creazione file_hostlist a seconda della lista ottenuta da file_logins
with open (file_hostlist,"w") as f:
    for row in logins:
        f.write(row.split(",")[1] + "\n")
