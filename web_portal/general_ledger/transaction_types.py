"""
SAP B1 Transaction Type Mappings

Based on SAP Business One standard object codes.
TransType in OJDT corresponds to ObjectCode for different document types.
"""

TRANSACTION_TYPE_MAP = {
    # Financial Documents
    '30': 'Journal Entry',
    '46': 'Opening Balance',
    
    # Sales Documents
    '13': 'A/R Invoice',
    '14': 'A/R Credit Memo',
    '15': 'Delivery',
    '16': 'Returns',
    '17': 'Sales Order',
    '23': 'Sales Quotation',
    '540000006': 'Sales Blanket Agreement',
    
    # Purchasing Documents
    '18': 'A/P Invoice',
    '19': 'A/P Credit Memo',
    '20': 'Goods Receipt PO',
    '21': 'Goods Return',
    '22': 'Purchase Order',
    '540000005': 'Purchase Blanket Agreement',
    
    # Inventory Documents
    '59': 'Goods Receipt',
    '60': 'Goods Issue',
    '67': 'Inventory Transfer',
    '69': 'Landing Costs',
    '310000001': 'Inventory Posting',
    
    # Banking & Payments
    '24': 'Incoming Payment',
    '46': 'Outgoing Payment',
    '162': 'Deposit',
    '163': 'Check for Payment',
    
    # Other Documents
    '202': 'Production Order',
    '204': 'Assembly/Disassembly',
    '1250000001': 'Inventory Count',
    '1470000049': 'Service Call',
    '1470000071': 'Service Contract',
    '1470000094': 'Equipment Card',
    
    # Special Types
    '-2': 'Adjustment',
    '-3': 'Closing',
}


def get_transaction_type_name(trans_type):
    """
    Get the human-readable name for a transaction type code.
    
    Args:
        trans_type: Transaction type code (int or str)
    
    Returns:
        Human-readable transaction type name
    """
    trans_type_str = str(trans_type).strip()
    return TRANSACTION_TYPE_MAP.get(trans_type_str, f'Type {trans_type_str}')


# Export this for use in other modules
__all__ = ['TRANSACTION_TYPE_MAP', 'get_transaction_type_name']
