# app/routers/movimientos.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/movimientos", tags=["movimientos"])

@router.get("/", response_model=List[schemas.Movimiento])
def leer_movimientos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Obtener lista de todos los movimientos.
    """
    movimientos = crud.get_movimientos(db, skip=skip, limit=limit)
    return movimientos

@router.get("/producto/{producto_id}", response_model=List[schemas.Movimiento])
def leer_movimientos_producto(
    producto_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener movimientos de un producto específico.
    """
    movimientos = crud.get_movimientos_por_producto(db, producto_id=producto_id)
    return movimientos

@router.post("/", response_model=schemas.Movimiento)
def crear_movimiento(
    movimiento: schemas.MovimientoCreate,
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo movimiento (entrada o salida).
    """
    try:
        return crud.crear_movimiento(db=db, movimiento=movimiento)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/entrada-rapida")
def entrada_rapida(
    producto_id: int,
    cantidad: int,
    motivo: str = "Entrada rápida",
    db: Session = Depends(get_db)
):
    """
    Registrar una entrada rápida de productos.
    """
    movimiento = schemas.MovimientoCreate(
        producto_id=producto_id,
        tipo="entrada",
        cantidad=cantidad,
        motivo=motivo,
        usuario="admin"
    )
    
    try:
        resultado = crud.crear_movimiento(db=db, movimiento=movimiento)
        return {
            "message": "Entrada registrada exitosamente",
            "movimiento_id": resultado.id,
            "stock_actual": resultado.producto.stock_actual
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/salida-rapida")
def salida_rapida(
    producto_id: int,
    cantidad: int,
    motivo: str = "Salida rápida",
    db: Session = Depends(get_db)
):
    """
    Registrar una salida rápida de productos.
    """
    movimiento = schemas.MovimientoCreate(
        producto_id=producto_id,
        tipo="salida",
        cantidad=cantidad,
        motivo=motivo,
        usuario="admin"
    )
    
    try:
        resultado = crud.crear_movimiento(db=db, movimiento=movimiento)
        return {
            "message": "Salida registrada exitosamente",
            "movimiento_id": resultado.id,
            "stock_actual": resultado.producto.stock_actual
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # app/routers/movimientos.py (agregar al final del archivo)

# app/routers/movimientos.py (modificar el endpoint /salida-multiple)

@router.post("/salida-multiple", response_model=List[schemas.Movimiento])
def crear_salida_multiple(
    salida: schemas.SalidaMultipleCreate,
    db: Session = Depends(get_db)
):
    """
    Crear una salida con múltiples productos.
    """
    try:
        # Preparar lista de productos
        productos_lista = [
            {
                'producto_id': item['producto_id'],
                'cantidad': item['cantidad']
            }
            for item in salida.productos
        ]
        
        # Usar la nueva función de crud
        movimientos = crud.crear_salida_multiple(
            db=db,
            productos=productos_lista,
            destino=salida.destino,
            razon=salida.razon,
            observaciones=salida.observaciones,
            usuario=salida.usuario
        )
        
        return movimientos
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")