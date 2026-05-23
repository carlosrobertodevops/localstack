import azure.functions as func
import json


def hello(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"message": "Hello from LocalStack-emulated Azure Function"}),
        mimetype="application/json",
        status_code=200,
    )
