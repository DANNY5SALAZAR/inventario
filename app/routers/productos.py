# app/routers/productos.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, schemas
from ..database import get_db
from ..utils.codigos import generar_codigo_barras, generar_qr_code
from fastapi.responses import JSONResponse
from fastapi import status

router = APIRouter(prefix="/productos", tags=["productos"])

@router.get("/", response_model=List[schemas.Producto])
def leer_productos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Obtener lista de todos los productos.
    """
    productos = crud.get_productos(db, skip=skip, limit=limit)
    return productos

@router.get("/buscar", response_model=List[schemas.Producto])
def buscar_productos(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    db: Session = Depends(get_db)
):
    """
    Buscar productos por nombre, código o descripción.
    """
    print(f"=== BUSQUEDA RECIBIDA ===")
    print(f"Término: {q}")
    print(f"Tipo: {type(q)}")
    
    productos = crud.buscar_productos(db, query=q)
    
    print(f"Productos encontrados: {len(productos)}")
    for p in productos:
        print(f"  - {p.codigo}: {p.nombre}")
    
    return productos
@router.get("/{producto_id}", response_model=schemas.Producto)
def leer_producto(producto_id: int, db: Session = Depends(get_db)):
    """
    Obtener un producto por su ID.
    """
    db_producto = crud.get_producto(db, producto_id=producto_id)
    if db_producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return db_producto

@router.get("/codigo/{codigo}", response_model=schemas.Producto)
def leer_producto_por_codigo(codigo: str, db: Session = Depends(get_db)):
    """
    Obtener un producto por su código.
    """
    db_producto = crud.get_producto_por_codigo(db, codigo=codigo)
    if db_producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return db_producto

@router.post("/", response_model=schemas.Producto, status_code=status.HTTP_201_CREATED)
def crear_producto(
    producto: schemas.ProductoCreate,
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo producto.
    Si no se proporciona código, se generará automáticamente.
    """
    # Verificar si el código ya existe
    if producto.codigo:
        existente = crud.get_producto_por_codigo(db, codigo=producto.codigo)
        if existente:
            raise HTTPException(status_code=400, detail="El código ya existe")

    nuevo_producto = crud.crear_producto(db=db, producto=producto)
    return nuevo_producto

@router.put("/{producto_id}", response_model=schemas.Producto)
def actualizar_producto(
    producto_id: int,
    producto: schemas.ProductoUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualizar un producto existente.
    """
    db_producto = crud.actualizar_producto(db, producto_id=producto_id, producto=producto)
    if db_producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return db_producto

@router.delete("/{producto_id}")
def eliminar_producto(producto_id: int, db: Session = Depends(get_db)):
    """
    Eliminar un producto.
    """
    success = crud.eliminar_producto(db, producto_id=producto_id)
    if not success:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"message": "Producto eliminado exitosamente"}

@router.get("/{producto_id}/codigo-barras")
def obtener_codigo_barras(producto_id: int, db: Session = Depends(get_db)):
    """
    Obtener imagen de código de barras para un producto.
    """
    producto = crud.get_producto(db, producto_id=producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    barcode = generar_codigo_barras(producto.codigo)
    if not barcode:
        raise HTTPException(status_code=500, detail="Error generando código de barras")
    
    return {"codigo_barras": barcode}

@router.get("/{producto_id}/qr-code")
def obtener_qr_code(producto_id: int, db: Session = Depends(get_db)):
    """
    Obtener código QR para un producto.
    """
    producto = crud.get_producto(db, producto_id=producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    qr = generar_qr_code(producto.codigo, {"nombre": producto.nombre, "precio": producto.precio_unitario})
    if not qr:
        raise HTTPException(status_code=500, detail="Error generando código QR")
    
    return {"qr_code": qr}