# -*- coding: utf-8 -*-
{
    'name': "Financiera - Interes en cuenta corriente",

    'summary': """
        Gestion de intereses en cuenta corriente con saldo negativo.""",

    'description': """
        Gestion de intereses en cuenta corriente con saldo negativo.
        Posibilidad de parametrizar periodo, capitalizacion, tasa, etc.
    """,

    'author': "Librasoft",
    'website': "http://libra-soft.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'financial',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['financiera_base'],

    # always loaded
    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'data/defaultdata.xml',
        'wizards/financiera_descubierto_wizard_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}