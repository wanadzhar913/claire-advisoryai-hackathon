"""
Sankey diagram utility functions.

**NOTE:** Need to handle edge cases where credits and debits for a period is 0.
"""
from typing import Dict, Any

import pandas as pd


def to_sankey(transactions: list[dict[str, Any]]) -> Dict[str, Any] :
    df = pd.DataFrame(transactions)

    # Handle empty transactions
    if len(df) == 0:
        return {'nodes': [{'id': 'acct', 'label': 'Main Account', 'type': 'account'}], 'links': []}

    # Normalize amount
    df['amount'] = df['amount'].astype(float)

    # Identify income sources (credits)
    income = df[df['transaction_type'] == 'credit']
    income_map = income.groupby('merchant_name')['amount'].sum().to_dict()

    # Identify spending (debits)
    debits = df[df['transaction_type'] == 'debit']
    category_map = debits.groupby('category')['amount'].sum().to_dict()

    # Build nodes
    nodes = [{'id': 'acct', 'label': 'Main Account', 'type': 'account'}]

    # Add sources
    for src in income_map:
        nodes.append({'id': f'in_{src.lower().replace(" ", "_")}', 'label': src, 'type': 'source'})

    # Add categories
    for cat in category_map:
        nodes.append({'id': f'cat_{cat.lower()}', 'label': cat.title(), 'type': 'sink'})

    # Build links (source → acct)
    links = [
        {'source': f'in_{src.lower().replace(" ", "_")}', 'target': 'acct', 'value': float(val)}
        for src, val in income_map.items()
    ]

    # Build links (acct → category)
    links += [
        {'source': 'acct', 'target': f'cat_{cat.lower()}', 'value': float(val)}
        for cat, val in category_map.items()
    ]

    return {'nodes': nodes, 'links': links}
