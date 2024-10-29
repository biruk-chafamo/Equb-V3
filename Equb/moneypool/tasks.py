from background_task import background
from .models import Equb


@background()
def select_winner_task(equb_name):
    equb = Equb.objects.get(name=equb_name)
    equb.balance_manager.select_winner()
    print("Winner selected ----------------------")
    
    