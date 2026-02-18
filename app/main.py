# app/main.py
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from .database import get_db, init_db
from . import crud, schemas
from .routers import productos, movimientos, inventario
from sqlalchemy.orm import Session
from app.routers import inventario as dashboard_router

# ===== Inicializar base de datos al iniciar la app (sin bloquear) =====
init_db()  # Se ejecuta antes de crear la app

# ===== Crear app =====
app = FastAPI(
    title="Sistema de Inventario FIMLM",
    description="Gestión de inventario con códigos QR y escaneo por cámara",
    version="1.0.0"
)

# ===== Archivos estáticos y templates =====
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# ===== Routers API =====
app.include_router(productos.router, prefix="/api")
app.include_router(movimientos.router, prefix="/api")
app.include_router(inventario.router, prefix="/api")
app.include_router(dashboard_router.router, prefix="/api")

# ===== RUTAS FRONTEND =====
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Inventario FIMLM"})

@app.get("/productos", response_class=HTMLResponse)
async def pagina_productos(request: Request):
    return templates.TemplateResponse("productos.html", {"request": request, "title": "Productos"})

@app.get("/productos/crear", response_class=HTMLResponse)
async def pagina_crear_producto(request: Request):
    return templates.TemplateResponse("crear_producto.html", {"request": request, "title": "Crear Producto"})
@app.get("/productos/cargar-excel", response_class=HTMLResponse)
async def pagina_cargar_excel(request: Request):
    return templates.TemplateResponse("cargar_excel.html", {"request": request, "title": "Carga Masiva de Productos"})

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
    producto = crud.get_producto(db, producto_id=producto_id)
    if not producto:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "title": "Error", "error": "Producto no encontrado"},
            status_code=404
        )
    historial = crud.get_movimientos_por_producto(db, producto_id=producto_id)
    return templates.TemplateResponse(
        "detalle_producto.html",
        {"request": request, "title": f"Producto: {producto.nombre}", "producto": producto, "historial": historial}
    )

@app.get("/productos/{producto_id}/editar", response_class=HTMLResponse)
async def pagina_editar_producto(request: Request, producto_id: int, db: Session = Depends(get_db)):
    producto = crud.get_producto(db, producto_id=producto_id)
    if not producto:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "title": "Error", "error": "Producto no encontrado"},
            status_code=404
        )
    return templates.TemplateResponse(
        "editar_producto.html",
        {"request": request, "title": f"Editar: {producto.nombre}", "producto": producto}
    )

@app.get("/productos/cargar-excel", response_class=HTMLResponse)
async def pagina_cargar_excel(request: Request):
    return templates.TemplateResponse("cargar_excel.html", {"request": request, "title": "Cargar Productos desde Excel"})

# ===== REDIRECCIONES =====
@app.get("/volver-a-productos")
async def volver_a_productos():
    return RedirectResponse(url="/productos")

@app.get("/volver-a-inicio")
async def volver_a_inicio():
    return RedirectResponse(url="/")

# ===== API =====
@app.get("/api/test")
async def test_endpoint():
    return {"message": "¡Sistema de Inventario funcionando!", "status": "ok", "version": "1.0.0"}

@app.post("/api/escanear")
async def procesar_codigo_escaneado(codigo: schemas.CodigoEscaneado, db: Session = Depends(get_db)):
    producto = crud.get_producto_por_codigo(db, codigo.codigo)
    if producto:
        return {
            "encontrado": True,
            "producto": producto,
            "mensaje": f"Producto encontrado: {producto.nombre}",
            "stock_actual": producto.stock_actual,
            "accion_sugerida": codigo.tipo_operacion
        }
    return {"encontrado": False, "codigo": codigo.codigo, "mensaje": "Producto no encontrado.", "accion_sugerida": "crear_producto"}

# ===== Manejo de errores =====
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
    if request.url.path.startswith('/api'):
        return JSONResponse(status_code=404, content={"message": "Recurso no encontrado"})
    return templates.TemplateResponse("error.html", {"request": request, "title": "404 - No encontrado", "error": "La página que buscas no existe"}, status_code=404)

@app.exception_handler(500)
async def internal_exception_handler(request: Request, exc):
    if request.url.path.startswith('/api'):
        return JSONResponse(status_code=500, content={"message": "Error interno del servidor"})
    return templates.TemplateResponse("error.html", {"request": request, "title": "500 - Error interno", "error": "Ha ocurrido un error interno en el servidor"}, status_code=500)

# ===== EJECUTAR LOCAL =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


