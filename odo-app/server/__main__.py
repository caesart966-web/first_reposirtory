import uvicorn

from .config import HOST, PORT

if __name__ == "__main__":
    print(f"ОДО-проверка: http://{HOST}:{PORT}")
    uvicorn.run("server.main:app", host=HOST, port=PORT, reload=False)
