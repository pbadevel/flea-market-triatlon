from fastapi import APIRouter, Query, Form, File, Depends, UploadFile, HTTPException
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload, selectinload

from src.kit.database.service import database_service
from src.repositories import AdRepository
from src.models import Ad

router = APIRouter(prefix="/test-msg", tags=["tg-test-msg"])
