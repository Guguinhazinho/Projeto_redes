import json
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import sqlite3
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI()

# Modelo de dados para uma nota
class Nota(BaseModel):
    titulo: str
    conteudo: str

@app.post("/nota/", response_model=Nota)
def criar_nota(nota: Nota):
    # Simulando a criação da nota e retornando a nota criada
    return nota

@app.get("/notas/", response_model=list[Nota])
def listar_notas():
    notas = [
        {"titulo": "Nota 1", "conteudo": "Conteúdo da nota 1"},
        {"titulo": "Nota 2", "conteudo": "Conteúdo da nota 2"}
    ]
    return notas


# Gerenciar conexões websocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_message(f"Mensagem recebida: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        
app = FastAPI(
    title="API de Notas Rápidas",
    description="Gerencie suas notas de forma simples!",
    version="1.0"
)

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message["type"]
            message_data = message["data"]

            if message_type == "auth":
                # Lógica de autenticação
                token = message_data["token"]
                # Validação do token...
            
            elif message_type == "create_note":
                # Lógica de criação de nota
                titulo = message_data["titulo"]
                conteudo = message_data["conteudo"]
                # Criação da nota no banco de dados...
            
            elif message_type == "update_note":
                # Lógica de atualização de nota
                note_id = message_data["id"]
                titulo = message_data["titulo"]
                conteudo = message_data["conteudo"]
                # Atualização da nota no banco de dados...
            
            elif message_type == "delete_note":
                # Lógica de exclusão de nota
                note_id = message_data["id"]
                # Exclusão da nota no banco de dados...

            # Enviar resposta informativa para o cliente
            await manager.send_message(json.dumps({
                "type": "info",
                "data": {
                    "message": "Operação realizada com sucesso!"
                }
            }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Servir arquivos estáticos (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/notas/", summary="Listar todas as notas")
def listar_notas():
    # Busca as notas no banco de dados
    notas = [
        {"id": 1, "titulo": "Nota 1", "conteudo": "Conteúdo 1"},
        {"id": 2, "titulo": "Nota 2", "conteudo": "Conteúdo 2"}
    ]
    # Retorna as notas em formato JSON
    return notas


@app.get("/", response_class=HTMLResponse)
def get_home():
    return open("static/index.html", encoding="utf-8").read()

# Conectar ao banco SQLite
conn = sqlite3.connect("notas.db", check_same_thread=False)
cursor = conn.cursor()

# Criar tabela de notas
cursor.execute("""
CREATE TABLE IF NOT EXISTS notas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    conteudo TEXT NOT NULL
)
""")

# Criar tabela de notas com um campo para armazenar o usuário dono da nota
cursor.execute("""
CREATE TABLE IF NOT EXISTS notas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    conteudo TEXT NOT NULL,
    usuario_id INTEGER NOT NULL
)
""")
conn.commit()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "sua_chave_secreta"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class Nota(BaseModel):
    titulo: str
    conteudo: str

class Usuario(BaseModel):
    username: str
    senha: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str = None

def criar_token_acesso(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def obter_usuario_atual(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Credenciais inválidas")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

@app.post("/registro/", summary="Registrar um novo usuário", description="Adiciona um novo usuário ao banco de dados.")
def registrar_usuario(usuario: Usuario):
    senha_hash = pwd_context.hash(usuario.senha)
    try:
        cursor.execute("INSERT INTO usuarios (username, senha) VALUES (?, ?)", (usuario.username, senha_hash))
        conn.commit()
        return {"mensagem": "Usuário registrado com sucesso!"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Usuário já existe")

@app.post("/login/", response_model=Token, summary="Autenticar um usuário", description="Autentica um usuário e retorna um token de acesso.")
def login_usuario(form_data: OAuth2PasswordRequestForm = Depends()):
    cursor.execute("SELECT * FROM usuarios WHERE username = ?", (form_data.username,))
    usuario = cursor.fetchone()
    if not usuario or not pwd_context.verify(form_data.password, usuario[2]):
        raise HTTPException(status_code=400, detail="Usuário ou senha incorretos")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = criar_token_acesso(data={"sub": usuario[1]}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/nota/", summary="Criar uma nova nota")
def criar_nota(nota: Nota, usuario: str = Depends(obter_usuario_atual)):
    # Buscar o ID do usuário
    cursor.execute("SELECT id FROM usuarios WHERE username = ?", (usuario,))
    usuario_id = cursor.fetchone()
    if not usuario_id:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    # Inserir nota associada ao usuário
    cursor.execute("INSERT INTO notas (titulo, conteudo, usuario_id) VALUES (?, ?, ?)",
                   (nota.titulo, nota.conteudo, usuario_id[0]))
    conn.commit()
    return {"mensagem": "Nota criada com sucesso!"}


@app.get("/notas/", summary="Listar notas do usuário logado")
def listar_notas(usuario: str = Depends(obter_usuario_atual)):
    # Buscar o ID do usuário
    cursor.execute("SELECT id FROM usuarios WHERE username = ?", (usuario,))
    usuario_id = cursor.fetchone()
    if not usuario_id:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    # Buscar apenas as notas do usuário logado
    cursor.execute("SELECT id, titulo, conteudo FROM notas WHERE usuario_id = ?", (usuario_id[0],))
    notas = cursor.fetchall()
    return [{"id": n[0], "titulo": n[1], "conteudo": n[2]} for n in notas]


@app.put("/nota/{nota_id}", summary="Atualizar uma nota do usuário logado")
def atualizar_nota(nota_id: int, nota: Nota, usuario: str = Depends(obter_usuario_atual)):
    # Buscar o ID do usuário
    cursor.execute("SELECT id FROM usuarios WHERE username = ?", (usuario,))
    usuario_id = cursor.fetchone()
    if not usuario_id:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    # Verificar se a nota pertence ao usuário autenticado
    cursor.execute("SELECT usuario_id FROM notas WHERE id = ?", (nota_id,))
    dono = cursor.fetchone()
    if not dono or dono[0] != usuario_id[0]:
        raise HTTPException(status_code=403, detail="Você não tem permissão para alterar esta nota")

    # Atualizar a nota
    cursor.execute("UPDATE notas SET titulo = ?, conteudo = ? WHERE id = ?",
                   (nota.titulo, nota.conteudo, nota_id))
    conn.commit()
    return {"mensagem": "Nota atualizada com sucesso!"}

@app.delete("/nota/{nota_id}", summary="Excluir uma nota do usuário logado")
def deletar_nota(nota_id: int, usuario: str = Depends(obter_usuario_atual)):
    # Buscar o ID do usuário
    cursor.execute("SELECT id FROM usuarios WHERE username = ?", (usuario,))
    usuario_id = cursor.fetchone()
    if not usuario_id:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    # Verificar se a nota pertence ao usuário autenticado
    cursor.execute("SELECT usuario_id FROM notas WHERE id = ?", (nota_id,))
    dono = cursor.fetchone()
    if not dono or dono[0] != usuario_id[0]:
        raise HTTPException(status_code=403, detail="Você não tem permissão para excluir esta nota")

    # Excluir a nota
    cursor.execute("DELETE FROM notas WHERE id = ?", (nota_id,))
    conn.commit()
    return {"mensagem": "Nota excluída com sucesso!"}

@app.put("/nota/{nota_id}", summary="Atualizar uma nota do usuário logado")
def atualizar_nota(nota_id: int, nota: Nota, usuario: str = Depends(obter_usuario_atual)):
    # Buscar o ID do usuário
    cursor.execute("SELECT id FROM usuarios WHERE username = ?", (usuario,))
    usuario_id = cursor.fetchone()
    if not usuario_id:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    # Verificar se a nota pertence ao usuário autenticado
    cursor.execute("SELECT usuario_id FROM notas WHERE id = ?", (nota_id,))
    dono = cursor.fetchone()
    if not dono or dono[0] != usuario_id[0]:
        raise HTTPException(status_code=403, detail="Você não tem permissão para alterar esta nota")

    # Atualizar a nota
    cursor.execute("UPDATE notas SET titulo = ?, conteudo = ? WHERE id = ?",
                   (nota.titulo, nota.conteudo, nota_id))
    conn.commit()
    return {"mensagem": "Nota atualizada com sucesso!"}

@app.delete("/nota/{nota_id}", summary="Excluir uma nota do usuário logado")
def deletar_nota(nota_id: int, usuario: str = Depends(obter_usuario_atual)):
    # Buscar o ID do usuário
    cursor.execute("SELECT id FROM usuarios WHERE username = ?", (usuario,))
    usuario_id = cursor.fetchone()
    if not usuario_id:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    # Verificar se a nota pertence ao usuário autenticado
    cursor.execute("SELECT usuario_id FROM notas WHERE id = ?", (nota_id,))
    dono = cursor.fetchone()
    if not dono or dono[0] != usuario_id[0]:
        raise HTTPException(status_code=403, detail="Você não tem permissão para excluir esta nota")

    # Excluir a nota
    cursor.execute("DELETE FROM notas WHERE id = ?", (nota_id,))
    conn.commit()
    return {"mensagem": "Nota excluída com sucesso!"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
