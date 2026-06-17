# src/kit/search.py
from typing import Optional, List
from sqlalchemy import Column, or_, and_
from sqlalchemy.sql.elements import ClauseElement
from datetime import datetime, timedelta

class SearchBuilder:
    @staticmethod
    def build_text_search(
        columns: List[Column],
        search_term: str,
        exact_match: bool = False
    ) -> ClauseElement:
        """
        Build a text search condition across multiple columns
        
        Args:
            columns: List of SQLAlchemy columns to search
            search_term: The search term
            exact_match: If True, use equals instead of LIKE
        
        Returns:
            SQLAlchemy filter condition
        """
        if exact_match:
            # For ID or exact username matching
            try:
                # Try to parse as integer for ID
                search_id = int(search_term)
                return columns[0] == search_id
            except ValueError:
                # Exact text match
                return or_(*[col == search_term for col in columns])
        else:
            # Partial match with LIKE
            search_pattern = f"%{search_term}%"
            return or_(*[col.ilike(search_pattern) for col in columns])
    
    @staticmethod
    def build_date_range(
        column: Column,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[ClauseElement]:
        """Build date range filter"""
        conditions = []
        if start_date:
            conditions.append(column >= start_date)
        if end_date:
            conditions.append(column <= end_date)
        
        if conditions:
            return and_(*conditions)
        return None
    
    @staticmethod
    def build_status_filter(
        status_column: Column,
        status: str,
        expires_column: Optional[Column] = None
    ) -> Optional[ClauseElement]:
        """Build status filter with special handling for 'active'"""
        if status == 'active':
            return and_(
                status_column == 'active',
                expires_column >= datetime.utcnow()
            )
        elif status == 'expired':
            return or_(
                status_column == 'expired',
                and_(
                    status_column == 'active',
                    expires_column < datetime.utcnow()
                )
            )
        elif status == 'none':
            return status_column.is_(None)
        else:
            return status_column == status