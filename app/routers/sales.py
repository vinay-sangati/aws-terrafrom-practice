import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product
from app.models.sale import Sale
from app.models.user import User
from app.schemas.sale import SaleCreate, SaleRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(payload: SaleCreate, db: Session = Depends(get_db)) -> Sale:
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if product.stock_quantity < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock (available: {product.stock_quantity})",
        )
    unit_price = product.price
    total = unit_price * Decimal(payload.quantity)
    product.stock_quantity -= payload.quantity
    sale = Sale(
        user_id=payload.user_id,
        product_id=payload.product_id,
        quantity=payload.quantity,
        unit_price=unit_price,
        total=total,
    )
    db.add(sale)
    db.commit()
    db.refresh(sale)
    logger.info("sale created id=%s user_id=%s product_id=%s", sale.id, sale.user_id, sale.product_id)
    return sale


@router.get("", response_model=list[SaleRead])
def list_sales(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[Sale]:
    return list(db.scalars(select(Sale).order_by(Sale.id.desc()).offset(skip).limit(limit)).all())


@router.get("/{sale_id}", response_model=SaleRead)
def get_sale(sale_id: int, db: Session = Depends(get_db)) -> Sale:
    sale = db.get(Sale, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")
    return sale
