# app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from . import models, schemas
from .utils.codigos import generar_codigo_producto

# ---------------------------
# CRUD Productos
# ---------------------------
def get_producto(db: Session, producto_id: int):
    return db.query(models.Producto).filter(models.Producto.id == producto_id).first()

def get_producto_por_codigo(db: Session, codigo: str):
    return db.query(models.Producto).filter(models.Producto.codigo == codigo).first()

def get_productos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Producto).offset(skip).limit(limit).all()

def crear_producto(db: Session, producto: schemas.ProductoCreate):
    if not producto.codigo:
        producto.codigo = generar_codigo_producto()
    
    db_producto = models.Producto(
        codigo=producto.codigo,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        categoria=producto.categoria,
        stock_minimo=producto.stock_minimo,
        stock_actual=0
    )
    
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto

def actualizar_producto(db: Session, producto_id: int, producto: schemas.ProductoUpdate):
    db_producto = get_producto(db, producto_id)
    if not db_producto:
        return None
    
    update_data = producto.dict(exclude_unset=True)
    
    # Solo actualizar atributos existentes
    for field, value in update_data.items():
        if hasattr(db_producto, field):
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


# CRUD Movimientos

def crear_movimiento(db: Session, movimiento: schemas.MovimientoCreate):
    producto = get_producto(db, movimiento.producto_id)
    if not producto:
        return None
    
    db_movimiento = models.Movimiento(
        producto_id=movimiento.producto_id,
        tipo=movimiento.tipo,
        cantidad=movimiento.cantidad,
        motivo=movimiento.motivo,
        tipo_origen=movimiento.tipo_origen,
        origen_nombre=movimiento.origen_nombre,  # Proveedor
        ubicacion=movimiento.ubicacion,  # Ubicación
        notas=movimiento.notas,  # Notas
        cliente_destino=movimiento.cliente_destino,  # 🆕 Para salidas
        usuario=movimiento.usuario,
       
    )
    
    if movimiento.tipo == "entrada":
        producto.stock_actual += movimiento.cantidad
    elif movimiento.tipo == "salida":
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

# ---------------------------
# Inventario y reportes
# ---------------------------
def get_productos_bajo_stock(db: Session):
    return db.query(models.Producto).filter(models.Producto.stock_actual < models.Producto.stock_minimo).all()

# ---------------------------
# Búsqueda de productos
# ---------------------------
def buscar_productos(db: Session, query: str):
    print(f"CRUD: Buscando '{query}'")
    
    query = query.lower()
    print(f"CRUD: Query en minúsculas: '{query}'")
    
    resultado = db.query(models.Producto).filter(
        (func.lower(models.Producto.nombre).like(f"%{query}%")) |
        (func.lower(models.Producto.codigo).like(f"%{query}%")) |
        (func.lower(func.coalesce(models.Producto.descripcion, '')).like(f"%{query}%"))
    ).all()
    
    print(f"CRUD: Encontrados {len(resultado)} productos")
    return resultado

# ---------------------------
# Salida múltiple
# ---------------------------
def crear_salida_multiple(db: Session, productos: list, destino: str, razon: str, observaciones: str = None, usuario: str = "admin"):
    movimientos_creados = []
    
    try:
        # Verificar stock
        for item in productos:
            producto = get_producto(db, item['producto_id'])
            if not producto:
                raise ValueError(f"Producto ID {item['producto_id']} no encontrado")
            if producto.stock_actual < item['cantidad']:
                raise ValueError(f"Stock insuficiente para {producto.nombre}. Solicitado: {item['cantidad']}, Disponible: {producto.stock_actual}")
        
        # Crear movimientos
        for item in productos:
            producto = get_producto(db, item['producto_id'])
            db_movimiento = models.Movimiento(
                producto_id=item['producto_id'],
                tipo="salida",
                cantidad=item['cantidad'],
                motivo=razon,
                notas=f"Destino: {destino}" + (f" - {observaciones}" if observaciones else ""),
                usuario=usuario
            )
            producto.stock_actual -= item['cantidad']
            db.add(db_movimiento)
            movimientos_creados.append(db_movimiento)
        
        db.commit()
        
        for movimiento in movimientos_creados:
            db.refresh(movimiento)
        
        return movimientos_creados
        
    except Exception as e:
        db.rollback()
        raise e
# app/crud.py - Agregar al final

def crear_entrada_multiple(
    db: Session, 
    productos: list, 
    tipo_origen: str, 
    origen_nombre: str, 
    ubicacion: str = None, 
    observaciones: str = None, 
    usuario: str = "admin"
):
    """
    Crear múltiples entradas de productos (compra, donación, devolución, etc.)
    """
    movimientos_creados = []
    
    try:
        for item in productos:
            producto = get_producto(db, item['producto_id'])
            if not producto:
                raise ValueError(f"Producto ID {item['producto_id']} no encontrado")
            
            # Crear movimiento
            db_movimiento = models.Movimiento(
                producto_id=item['producto_id'],
                tipo="entrada",
                cantidad=item['cantidad'],
                motivo=tipo_origen.capitalize(),
                tipo_origen=tipo_origen,
                origen_nombre=origen_nombre,
                ubicacion=ubicacion,
                notas=observaciones,
                usuario=usuario
            )
            
            # Actualizar stock
            producto.stock_actual += item['cantidad']
            
            db.add(db_movimiento)
            movimientos_creados.append(db_movimiento)
        
        db.commit()
        
        for movimiento in movimientos_creados:
            db.refresh(movimiento)
        
        return movimientos_creados
        
    except Exception as e:
        db.rollback()
        raise e
    
 
