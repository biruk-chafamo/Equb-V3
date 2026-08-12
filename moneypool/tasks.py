from background_task import background
from .models import Equb


@background()
def select_winner_task(equb_name):
    equb = Equb.objects.get(name=equb_name)
    from .services.settlement_service import select_winner
    select_winner(equb.balance_manager)
    
    