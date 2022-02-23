# Testing XSteam
# To be added to environment set-up: `pip install pyXSteam`

from iapws import IAPWS97
from pyXSteam.XSteam import XSteam

steamTable = XSteam(XSteam.UNIT_SYSTEM_MKS)
print(steamTable.hL_p(220.0))


# Testing iapws
# To be added to environment set-up: `pip install iapws`

sat_steam = IAPWS97(P=1, x=1)  # saturated steam with known P
sat_liquid = IAPWS97(T=370, x=0)  # saturated liquid with known T
steam = IAPWS97(P=2.5, T=500)  # steam with known P and T
print(sat_steam.h, sat_liquid.h, steam.h)  # calculated enthalpies
