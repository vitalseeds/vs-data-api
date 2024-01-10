import os
from pathlib import Path

import uvicorn

APP_DIR = Path(__file__).parents[2].absolute()
SSL_KEYFILE = Path(os.environ.get("SSL_KEYFILE", f"{APP_DIR}/ssl/localhost_key.pem")).resolve()
SSL_CERTFILE = Path(os.environ.get("SSL_CERTFILE", f"{APP_DIR}/ssl/localhost_cert.pem")).resolve()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8432,
        reload=True,
        ssl_keyfile=SSL_KEYFILE,
        ssl_certfile=SSL_CERTFILE,
    )
