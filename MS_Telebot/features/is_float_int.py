def is_float_int(digits):
    true_symbols = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '-']
    # Если он есть '-' и он стоит не вначале, возвращяет False
    if '-' in digits and digits.index('-') > 0:
        return False
    for symb in digits.replace(',', '.'):
        if symb not in true_symbols:
            return False
    return True