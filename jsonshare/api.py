# -*- coding: utf-8 -*-
# Copyright (c) 2019, SHS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import json
import requests
import os

# Permite trabajar con acentos, ñ, simbolos, etc
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


@frappe.whitelist(allow_guest=True)
def sumtwo(num1, num2):
    sumoftwo = int(num1) + int(num2)
    return sumoftwo


@frappe.whitelist(allow_guest=True)
def receivejson1(**kwargs):
    '''NO CAMBIAR'''
    kwargs=kwargs
    return kwargs


@frappe.whitelist(allow_guest=True)
def hello_world(**kwargs):
    '''NO CAMBIAR'''
    hello = 'Hello World'
    return hello

def compartir_data(data, usuario):
    # Obtiene la single table el metodo a ejecutar
    # Parametro 1 : Nombre doctype, Parametro 2: Nombre campo, parametro 3: deshabilida cache
    metodo_api = frappe.db.get_single_value('Configuracion JsonShare', 'nombre', cache=False)
    url = '{0}/{1}'.format(usuario, metodo_api)

    try:
        r = requests.post(url, data=json.dumps(data))
        # frappe.msgprint(_(json.dumps(data)))
    except:
        frappe.msgprint(_('Error'))
    else:
        frappe.msgprint(_(r.status_code))
        frappe.msgprint(_(r.content))

@frappe.whitelist()
def crud(item, usuario, doctype):
    '''Funcion encarga de obtener datos y mandarlos por HTTP
        funcionalidades extras'''
    # GET DATA
    if doctype == 'Item':
        try:
            item_data = frappe.db.get_values('Item',
                                            filters={'item_code': item},
                                            fieldname=['item_code', 'item_name',
                                                        'item_group', 'stock_uom',
                                                        'standard_rate', 'description',
                                                        'is_stock_item'], as_dict=1)
            compartir_data(item_data, usuario)
        except:
            frappe.msgprint(_('FAIL'))

    if doctype == 'Customer':
        try:
            # Obtiene informacion de Customer
            customer_data = frappe.db.get_values('Customer',
                                                 filters={'customer_name': item},
                                                 fieldname=['customer_name', 'territory',
                                                            'customer_group', 'customer_type'], as_dict=1)
            # Obtiene las direcciones con relacion al cliente
            dynamic_table = frappe.db.get_values('Dynamic Link',
                                                 filters={'link_name': item, 'link_doctype': 'Customer',
                                                          'parenttype': 'Address'},
                                                 fieldname=['parent'], as_dict=1)
            # Obtiene los contactos con relacion al cliente
            dynamic_table_contacts = frappe.db.get_values('Dynamic Link',
                                                          filters={'link_name': item, 'link_doctype': 'Customer',
                                                                   'parenttype': 'Contact'},
                                                          fieldname=['parent'], as_dict=1)

            n_address = len(dynamic_table)
            customer_address = []
            for i in range(0, n_address):
                # Obtiene las direcciones
                customer_address_data = frappe.db.get_values('Address',
                                                        filters={'name': dynamic_table[i]['parent']},
                                                        fieldname=['email_id', 'county', 'city',
                                                                   'address_line1', 'state', 'address_type',
                                                                   'address_title', 'phone', 'country'], as_dict=1)
                # Crea un array con todas las direcciones encontradas
                customer_address.append(customer_address_data)

            # Obtiene los contactos
            n_contact = len(dynamic_table_contacts)
            contact = []
            for i in range(0, n_contact):
                contact_data = frappe.db.get_values('Contact',
                                                    filters={'name': dynamic_table_contacts[i]['parent']},
                                                    fieldname=['email_id', 'first_name', 'last_name',
                                                               'phone', 'mobile_no'], as_dict=1)
                # Crea un array con todos los contactos encontrados
                contact.append(contact_data)

            # Funcion para preparar informacion y mandarla
            compartir_json_data(usuario, customer_data, customer_address, contact)
        except:
            frappe.msgprint(_('FAIL Customer'))


def guardar_dato_recibido(item_fields):
    # Guarda el numero de items recibidos a crear
    n_item = 0
    n_uom = 0
    mensaje = ''

    for item in item_fields:
        if not frappe.db.exists('Item', _(item.get('item_code'))):
            n_item = len(item_fields)
            new_item = frappe.new_doc('Item')
            new_item.item_code = _(item.get('item_code'))
            new_item.item_name = _(item.get('item_name'))
            new_item.description = _(item.get('description'))
            new_item.is_stock_item = _(item.get('is_stock_item'))

            if item.get('item_group') != 'All Item Groups':
                new_item.item_group = 'All Item Groups'
            else:
                new_item.item_group = _(item.get('item_group'))

            if not frappe.db.exists('UOM', _(item.get('stock_uom'))):
                new_stock_uom = frappe.new_doc("UOM")
                new_stock_uom.uom_name = _(item.get('stock_uom'))
                new_stock_uom.save(ignore_permissions=True)
                n_uom += 1
            else:
                new_item.stock_uom = _(item.get('stock_uom'))
            
            new_item.save(ignore_permissions=True)
            mensaje = '{0} Items creados, {1} UOM creados'.format(n_item, n_uom)
        else:
            mensaje = 'Item compartido ya existe'

    return mensaje


def compartir_json_data(usuario, customer_data, customer_address, contact):
    template_data = {}
    template_data['key'] = 'abc' #FIXME
    template_data['doctype'] = 'Customer'
    
    doctype_fields = {}
    doctype_fields['fields'] = customer_data[0]
    doctype_fields['addresses'] = []
    doctype_fields['contacts'] = []

    for i in customer_address:
        doctype_fields['addresses'].append(i[0])
        #frappe.msgprint(_(i[0]))
    
    for i in contact:
        doctype_fields['contacts'].append(i[0])
        #frappe.msgprint(_(i[0]))
    
    template_data['data'] = doctype_fields
    json_data = json.dumps(template_data)
    # frappe.msgprint(_(json_data))
    frappe.publish_realtime(event='eval_js', message='alert("{0}")'.format('funcionando'), user=frappe.session.user)
    # Obtiene la single table el metodo a ejecutar
    # Parametro 1 : Nombre doctype, Parametro 2: Nombre campo, parametro 3: deshabilida cache
    metodo_api = frappe.db.get_single_value('Configuracion JsonShare', 'nombre', cache=False)
    url = '{0}/{1}'.format(usuario, metodo_api)

    # frappe.msgprint(_(url))
    try:
        r = requests.post(url, data=json_data)
        # frappe.msgprint(_(json_data))
        # frappe.msgprint(_(url))
    except:
        frappe.msgprint(_('Error'))
    else:
        frappe.msgprint(_(r.status_code))
        frappe.msgprint(_(r.content))
    frappe.msgprint(_('Todas las categorías de clientes'))
        
@frappe.whitelist(allow_guest=True)
def receivejson(data):
    item_data = json.loads(data)
    #frappe.publish_realtime(event='global',message='Alguien llamo este metodo de receive json',room=None)
    mensaje = guardar_dato_recibido(item_data)
    frappe.publish_realtime(event='msgprint', message='alert("{0}")'.format('funcionando'), user=frappe.session.user)
    return mensaje


@frappe.whitelist(allow_guest=True)
def receivejson_customer(data):
    customer_data = json.loads(data)
    #frappe.publish_realtime(event='global',message='Alguien llamo este metodo de receive json',room=None)
    mensaje = create_customer(customer_data)
    frappe.publish_realtime(event='eval_js', message='alert("{0}")'.format('funcionando'), user=frappe.session.user)
    return mensaje


def mensaje():
    frappe.publish_realtime(event='msgprint',message='Alguien llamo este metodo de receive json')

def create_customer(data_customer):
    data = data_customer
    if data['doctype'] == 'Customer':
        # Cargamos todos los campos
        customer_json = data['data']
        # Cargamos los campos de customer
        customer_fields = customer_json['fields']
        new_customer = frappe.new_doc("Customer")
        new_customer.customer_name = 'Palito1'
        new_customer.customer_type = 'Company'
        new_customer.territory = 'All Territories'
        new_customer.customer_group = 'Individual'
        new_customer.save(ignore_permissions=True)          
        # Cargamos el array de direcciones
        # customer_addresses = customer_json['addresses']
        # for i in customer_addresses:
        #     doc = i
        #     new_object = frappe.get_doc(doc)
        #     new_object.insert(ignore_permissions=True)
        # # Cargamos el array de contactos
        # customer_contacts = customer_json['contacts']
        # for i in customer_contacts:
        #     doc = i
        #     new_object = frappe.get_doc(doc)
        #     new_object.insert(ignore_permissions=True)
        # datareturn = json.dumps(customer_addresses)
        # return datareturn

def create_customer_group(data_customer):
    pass
    # # find if customer group exists as sent
    # # if it exists, do not create it
    # # if it doesn't, we refer to root, so we create it under root
    # # we will separate the node groups created by a parent folder with the server address of the sender.    
    # # if parent_customer_group is None or parent == 'All Customer Groups'
    # # create the customer group
    # # else:
    # # find the customer group root
