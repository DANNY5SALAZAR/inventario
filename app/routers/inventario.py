# app/routers/inventario.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/inventario", tags=["inventario"])

@router.get("/reporte", response_model=schemas.ReporteInventario)
def obtener_reporte_inventario(db: Session = Depends(get_db)):
    """
    Obtener reporte completo del inventario.
    """
    productos = crud.get_productos(db)
    productos_bajo_stock = crud.get_productos_bajo_stock(db)
    valor_total = crud.get_valor_total_inventario(db)
    ultimos_movimientos = crud.get_movimientos(db, limit=10)
    
    return {
        "total_productos": len(productos),
        "productos_bajo_stock": productos_bajo_stock,
        "valor_total_inventario": valor_total,
        "ultimos_movimientos": ultimos_movimientos
    }

@router.get("/bajo-stock", response_model=List[schemas.Producto])
def obtener_productos_bajo_stock(db: Session = Depends(get_db)):
    """
    Obtener productos con stock por debajo del mínimo.
    """
    return crud.get_productos_bajo_stock(db)

@router.get("/valor-total")
def obtener_valor_total_inventario(db: Session = Depends(get_db)):
    """
    Obtener valor total del inventario.
    """
    valor = crud.get_valor_total_inventario(db)
    return {"valor_total_inventario": valor}

@router.get("/producto/{producto_id}/historial")
def obtener_historial_producto(
    producto_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener historial completo de un producto.
    """
    producto = crud.get_producto(db, producto_id=producto_id)
    if not producto:
        return {"error": "Producto no encontrado"}
    
    historial = crud.get_movimientos_por_producto(db, producto_id=producto_id)
    
    return {
        "producto": producto,
        "historial": historial,
        "total_movimientos": len(historial)
    }