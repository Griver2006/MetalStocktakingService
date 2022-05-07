from api_sheets import call_metals_prices

metal_types = dict(call_metals_prices())
print('Черный' in metal_types.keys())