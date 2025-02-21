from .auth import router as auth_router
from .trips import router as trips_router
from .dashboard import router as dashboard_router
from .packing import router as packing_router
# from .weather import router as weather_router
# from .shopping import router as shopping_router

routers = [auth_router, trips_router, dashboard_router, packing_router]
# packing_router, weather_router, shopping_router]
