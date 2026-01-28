# app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Producto(Base):
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, index=True, nullable=False)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    categoria = Column(String(100), nullable=True)
    precio_unitario = Column(Float, default=0.0)
    stock_minimo = Column(Integer, default=0)
    stock_actual = Column(Integer, default=0)
    ubicacion = Column(String(100), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relación con movimientos
    movimientos = relationship("Movimiento", back_populates="producto", cascade="all, delete-orphan")

class Movimiento(Base):
    __tablename__ = "movimientos"
    
    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    tipo = Column(String(20), nullable=False)  # 'entrada' o 'salida'
    cantidad = Column(Integer, nullable=False)
    motivo = Column(String(200), nullable=True)
    notas = Column(Text, nullable=True)
    usuario = Column(String(100), default="admin")
    fecha_movimiento = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación con producto
    producto = relationship("Producto", back_populates="movimientos")