#!/usr/bin/env python
#
# pyvminventory
#
# Author: Diego Mariani - dmariani (at) avantune.com
#

import pyVmomi

from pyVmomi import vim
from pyVmomi import vmodl

from pyVim.connect import SmartConnect, Disconnect

import os
import sys
import atexit
import ssl

import xml.etree.ElementTree as ET    # necessario per creazione file XML
from xml.dom import minidom    # necessario per creazione file XML

# Definizione percorsi files e directory necessari per l'esecuzione
fileLogins = "/opt/pyvminventory/logins.txt"    # all'interno del file inserire campo con tipologia di virtualizzatore (ESX o LXC)
fileLablist = "/var/www/html/pyvminventory/lablist.txt"
dirXml = "/var/www/html/pyvminventory/xml/"

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
check_path_exists(fileLogins, fileLablist, dirXml)

# Definizione funzione per normalizzazione file fileLogins e creazione lista
def norm_logins():
    with open (fileLogins,"r") as f:
        return map(str.strip,f.readlines())    # strip \n alla fine di ogni elemento della lista

# Assegnazione lista ottenuta dalla manipolazione di fileLogins
logins = norm_logins()

# Definizione funzione per connettersi ad un ESX che ritorna una lista nested che contiene tutte le vm ed i relativi dettagli
def connectorEsx(host, user, pwd):
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
def connectorLxc(host, user, pwd):
    pass

# Definizione funzione che costruisce un file XML, prendendo in input l'output (liste nested) delle funzioni connectorEsx e connectorLxc
def xmlConstructor(host, args):
    xml_lab = ET.Element("lab")    # Definizione radice dell'albero XML
    i = 0
    while i < len(args):
        xml_vm = ET.SubElement(xml_lab, "vm")    # vm
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
    xml_reparsed = minidom.parseString(ET.tostring(xml_lab, encoding="utf-8"))    # Somma di tutti i nodi per costruzione albero XML
    xml_tree = xml_reparsed.toprettyxml(indent="  ", encoding="utf-8")    # Aggiunta prolog iniziale e indentazioni all'albero XML
    with open(dirXml + host + ".xml", "wb") as f:
        f.write(xml_tree)

# Meccanismo che si occupa di indirizzare al giusto connettore a seconda del contenuto di fileLogins (ESX o LXC)
for row in logins:
    hypervisor = row.split(",")[0]
    host = row.split(",")[1]
    user = row.split(",")[2]
    pwd = row.split(",")[3]
    if hypervisor == "esx":
        xmlConstructor(host, connectorEsx(host, user, pwd))
    elif hypervisor == "lxc":
        xmlConstructor(host, connectorLxc(host, user, pwd))
    else:
        pass

# Assegnazione lista ottenuta dalla manipolazione di fileLogins
logins = norm_logins()
# Creazione fileLablist a seconda della lista ottenuta da fileLogins
with open (fileLablist,"w") as f:
    for row in logins:
        f.write(row.split(",")[1] + "\n")
