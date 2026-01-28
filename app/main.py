# app/main.py
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from contextlib import asynccontextmanager
from .database import get_db, init_db
from . import crud, schemas
from .routers import productos, movimientos, inventario
from sqlalchemy.orm import Session
from fastapi import HTTPException

# Lifespan para manejar eventos de inicio/cierre
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando Sistema de Inventario...")
    init_db()  # Crear tablas si no existen
    print("✅ Base de datos inicializada")
    yield
    # Shutdown
    print("👋 Cerrando aplicación...")

# Crear app
app = FastAPI(
    title="Sistema de Inventario QR",
    description="Gestión de inventario con códigos QR y escaneo por cámara",
    version="1.0.0",
    lifespan=lifespan
)

# Archivos estáticos y templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Routers API
app.include_router(productos.router, prefix="/api")
app.include_router(movimientos.router, prefix="/api")
app.include_router(inventario.router, prefix="/api")

# ========== RUTAS PARA EL FRONTEND ==========
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Inventario QR"})

@app.get("/productos", response_class=HTMLResponse)
async def pagina_productos(request: Request):
    return templates.TemplateResponse("productos.html", {"request": request, "title": "Productos"})

@app.get("/productos/crear", response_class=HTMLResponse)
async def pagina_crear_producto(request: Request):
    return templates.TemplateResponse("crear_producto.html", {"request": request, "title": "Crear Producto"})

@app.get("/entrada", response_class=HTMLResponse)
async def pagina_entrada(request: Request):
    return templates.TemplateResponse("entrada.html", {"request": request, "title": "Entrada de Productos"})

@app.get("/salida", response_class=HTMLResponse)
async def pagina_salida(request: Request):
    return templates.TemplateResponse("salida.html", {"request": request, "title": "Salida de Productos"})

@app.get("/movimientos", response_class=HTMLResponse)
async def pagina_movimientos(request: Request):
    return templates.TemplateResponse("movimientos.html", {"request": request, "title": "Movimientos"})

@app.get("/escanear", response_class=HTMLResponse)
async def pagina_escanear(request: Request):
    return templates.TemplateResponse("escanear.html", {"request": request, "title": "Escanear Códigos"})

@app.get("/productos/{producto_id}/detalle", response_class=HTMLResponse)
async def pagina_detalle_producto(request: Request, producto_id: int, db: Session = Depends(get_db)):
    """Página de detalle de un producto específico"""
    producto = crud.get_producto(db, producto_id=producto_id)
    if not producto:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "title": "Error",
                "error": "Producto no encontrado"
            },
            status_code=404
        )
    
    # Obtener historial del producto
    historial = crud.get_movimientos_por_producto(db, producto_id=producto_id)
    
    return templates.TemplateResponse(
        "detalle_producto.html",
        {
            "request": request,
            "title": f"Producto: {producto.nombre}",
            "producto": producto,
            "historial": historial
        }
    )

@app.get("/productos/{producto_id}/editar", response_class=HTMLResponse)
async def pagina_editar_producto(request: Request, producto_id: int, db: Session = Depends(get_db)):
    """Página para editar un producto existente"""
    producto = crud.get_producto(db, producto_id=producto_id)
    if not producto:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "title": "Error",
                "error": "Producto no encontrado"
            },
            status_code=404
        )
    
    return templates.TemplateResponse(
        "editar_producto.html",
        {
            "request": request,
            "title": f"Editar: {producto.nombre}",
            "producto": producto
        }
    )

# ========== RUTAS DE REDIRECCIÓN Y UTILIDAD ==========
@app.get("/volver-a-productos")
async def volver_a_productos():
    """Redirige a la página de productos"""
    return RedirectResponse(url="/productos")

@app.get("/volver-a-inicio")
async def volver_a_inicio():
    """Redirige a la página principal"""
    return RedirectResponse(url="/")

# ========== API PARA EL FRONTEND ==========
@app.get("/api/test")
async def test_endpoint():
    return {
        "message": "¡Sistema de Inventario funcionando!",
        "status": "ok",
        "version": "1.0.0",
        "features": [
            "Gestión de productos",
            "Registro de movimientos",
            "Códigos QR y barras",
            "Escaneo por cámara",
            "API REST completa"
        ]
    }

@app.post("/api/escanear")
async def procesar_codigo_escaneado(codigo: schemas.CodigoEscaneado, db=Depends(get_db)):
    producto = crud.get_producto_por_codigo(db, codigo.codigo)
    if producto:
        return {
            "encontrado": True,
            "producto": producto,
            "mensaje": f"Producto encontrado: {producto.nombre}",
            "stock_actual": producto.stock_actual,
            "accion_sugerida": codigo.tipo_operacion
        }
    else:
        return {
            "encontrado": False,
            "codigo": codigo.codigo,
            "mensaje": "Producto no encontrado. ¿Deseas crearlo?",
            "accion_sugerida": "crear_producto"
        }

@app.get("/api/dashboard")
async def obtener_dashboard(db=Depends(get_db)):
    productos = crud.get_productos(db)
    bajo_stock = crud.get_productos_bajo_stock(db)
    valor_total = crud.get_valor_total_inventario(db)
    ultimos_movimientos = crud.get_movimientos(db, limit=5)
    
    return {
        "total_productos": len(productos),
        "productos_bajo_stock": len(bajo_stock),
        "valor_total_inventario": valor_total,
        "ultimos_movimientos": ultimos_movimientos
    }

# ========== MANEJO DE ERRORES ==========
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
    # Si es una API, devuelve JSON
    if request.url.path.startswith('/api'):
        return JSONResponse(
            status_code=404,
            content={"message": "Recurso no encontrado"}
        )
    # Si es una página web, muestra template de error
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "title": "404 - No encontrado",
            "error": "La página que buscas no existe"
        },
        status_code=404
    )

@app.exception_handler(500)
async def internal_exception_handler(request: Request, exc):
    # Si es una API, devuelve JSON
    if request.url.path.startswith('/api'):
        return JSONResponse(
            status_code=500,
            content={"message": "Error interno del servidor"}
        )
    # Si es una página web, muestra template de error
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "title": "500 - Error interno",
            "error": "Ha ocurrido un error interno en el servidor"
        },
        status_code=500
    )

# ========== EJECUTAR LOCAL ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

