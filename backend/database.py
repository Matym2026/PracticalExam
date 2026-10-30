import os
from datetime import datetime, timezone

import boto3

# Sin Access Keys: boto3 usa automaticamente las credenciales temporales
# del IAM Role asociado a la instancia EC2.
TABLE_NAME = os.getenv("TABLE_NAME", "url-shortener")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
_table = _dynamodb.Table(TABLE_NAME)


def guardar_url(short_code: str, original_url: str) -> dict:
    item = {
        "short_code": short_code,
        "original_url": original_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _table.put_item(Item=item)
    return item


def obtener_url(short_code: str) -> dict | None:
    respuesta = _table.get_item(Key={"short_code": short_code})
    return respuesta.get("Item")
