from api_sheets import call_metals_prices
from data import db_session
from data.clean_weights import ButtonsCleanWeights


metal_types = dict(call_metals_prices())
kush_prices = dict(call_metals_prices(kush=True))
clean_weights_buttons = [name[0] for name in db_session.create_session().query(
    ButtonsCleanWeights.name_clean_weight).all()]

temp_operations = {}