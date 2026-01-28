# app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from . import models, schemas
from .utils.codigos import generar_codigo_producto

# Operaciones CRUD para Productos
def get_producto(db: Session, producto_id: int):
    return db.query(models.Producto).filter(models.Producto.id == producto_id).first()

def get_producto_por_codigo(db: Session, codigo: str):
    return db.query(models.Producto).filter(models.Producto.codigo == codigo).first()

def get_productos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Producto).offset(skip).limit(limit).all()

def crear_producto(db: Session, producto: schemas.ProductoCreate):
    # Generar código si no se proporciona
    if not producto.codigo:
        producto.codigo = generar_codigo_producto()
    
    # Crear objeto de base de datos
    db_producto = models.Producto(
        codigo=producto.codigo,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        categoria=producto.categoria,
        precio_unitario=producto.precio_unitario,
        stock_minimo=producto.stock_minimo,
        stock_actual=0,  # Empieza en 0
        ubicacion=producto.ubicacion
    )
    
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto

def actualizar_producto(db: Session, producto_id: int, producto: schemas.ProductoUpdate):
    db_producto = get_producto(db, producto_id)
    if not db_producto:
        return None
    
    # Actualizar solo los campos proporcionados
    update_data = producto.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_producto, field, value)
    
    db.commit()
    db.refresh(db_producto)
    return db_producto

def eliminar_producto(db: Session, producto_id: int):
    db_producto = get_producto(db, producto_id)
    if not db_producto:
        return False
    
    db.delete(db_producto)
    db.commit()
    return True

# Operaciones CRUD para Movimientos
def crear_movimiento(db: Session, movimiento: schemas.MovimientoCreate):
    # Verificar que el producto existe
    producto = get_producto(db, movimiento.producto_id)
    if not producto:
        return None
    
    # Crear movimiento
    db_movimiento = models.Movimiento(
        producto_id=movimiento.producto_id,
        tipo=movimiento.tipo,
        cantidad=movimiento.cantidad,
        motivo=movimiento.motivo,
        notas=movimiento.notas,
        usuario=movimiento.usuario
    )
    
    # Actualizar stock del producto
    if movimiento.tipo == "entrada":
        producto.stock_actual += movimiento.cantidad
    elif movimiento.tipo == "salida":
        # Verificar que hay suficiente stock
        if producto.stock_actual < movimiento.cantidad:
            raise ValueError("Stock insuficiente")
        producto.stock_actual -= movimiento.cantidad
    
    db.add(db_movimiento)
    db.commit()
    db.refresh(db_movimiento)
    return db_movimiento

def get_movimientos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Movimiento).order_by(desc(models.Movimiento.fecha_movimiento)).offset(skip).limit(limit).all()

def get_movimientos_por_producto(db: Session, producto_id: int):
    return db.query(models.Movimiento).filter(models.Movimiento.producto_id == producto_id).order_by(desc(models.Movimiento.fecha_movimiento)).all()

# Consultas de inventario
def get_productos_bajo_stock(db: Session):
    return db.query(models.Producto).filter(models.Producto.stock_actual < models.Producto.stock_minimo).all()

def get_valor_total_inventario(db: Session):
    """Calcula el valor total del inventario"""
    productos = db.query(models.Producto).all()
    valor_total = sum(producto.precio_unitario * producto.stock_actual for producto in productos)
    return valor_total or 0.0

def buscar_productos(db: Session, query: str):
    return db.query(models.Producto).filter(
        (models.Producto.nombre.ilike(f"%{query}%")) |
        (models.Producto.codigo.ilike(f"%{query}%")) |
        (models.Producto.descripcion.ilike(f"%{query}%"))
    ).all()
# app/crud.py (agregar al final)

def crear_salida_multiple(db: Session, productos: list, destino: str, razon: str, observaciones: str = None, usuario: str = "admin"):
    """
    Crear múltiples salidas en una sola transacción.
    """
    movimientos_creados = []
    
    try:
        # Verificar stock de todos los productos primero
        for item in productos:
            producto = get_producto(db, item['producto_id'])
            if not producto:
                raise ValueError(f"Producto ID {item['producto_id']} no encontrado")
            
            if producto.stock_actual < item['cantidad']:
                raise ValueError(
                    f"Stock insuficiente para {producto.nombre}. "
                    f"Solicitado: {item['cantidad']}, Disponible: {producto.stock_actual}"
                )
        
        # Crear todos los movimientos
        for item in productos:
            producto = get_producto(db, item['producto_id'])
            
            # Crear movimiento
            db_movimiento = models.Movimiento(
                producto_id=item['producto_id'],
                tipo="salida",
                cantidad=item['cantidad'],
                motivo=razon,
                notas=f"Destino: {destino}" + (f" - {observaciones}" if observaciones else ""),
                usuario=usuario
            )
            
            # Actualizar stock
            producto.stock_actual -= item['cantidad']
            
            db.add(db_movimiento)
            movimientos_creados.append(db_movimiento)
        
        db.commit()
        
        # Refrescar los objetos para obtener los IDs generados
        for movimiento in movimientos_creados:
            db.refresh(movimiento)
        
        return movimientos_creados
        
    except Exception as e:
        db.rollback()
        raise ValueError(str(e))