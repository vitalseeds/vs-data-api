from vs_data_api.main import app


def list_endpoints():
    for route in app.routes:
        print(route.path) # noqa
