from telegram import User as TGUser
from typing import Optional, List, Tuple
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import or_
from src.kit.repository.main import Options

from telegram import User as TGUser
from src.auth.init_data.types import InitData
from src.exceptions import BadRequest
from src.kit.pagination import PaginationParams
from src.models import User
from src.repositories.users import UserRepository


class UserService:
    async def get_list(
        self,
        session: AsyncSession,
        pagination: PaginationParams,
        search: Optional[str] = None,
        status: Optional[str] = None,
        with_subscriptions: Optional[bool] = None
    ) -> Tuple[List[User], int]:
        """
        Get paginated users with search and filters
        
        Args:
            session: Database session
            pagination: Pagination parameters
            search: Search term
            status: Subscription status filter
        
        Returns:
            Tuple of (users, total_count)
        """
        repository = UserRepository.from_session(session)
        options = []

        # if with_subscriptions:
        #     options.append(selectinload(User.subscription))

        return await repository.search_users(
            search_term=search,
            status=status,
            limit=pagination.limit,
            page=pagination.page,
            options = options
        )
    
    async def get_user_details(self, session: AsyncSession, user_id: int) -> Optional[User]:
        """Get detailed user information"""
        repository = UserRepository.from_session(session)
        # return await repository.get_user_with_details(user_id)
    
    async def search_users_by_name(
        self,
        session: AsyncSession,
        name: str,
        limit: int = 10
    ) -> List[User]:
        """Quick search by name only"""
        repository = UserRepository.from_session(session)
        stmt = repository.get_base_stmt().where(
            or_(
                User.first_name.ilike(f"%{name}%"),
                User.last_name.ilike(f"%{name}%")
            )
        ).limit(limit)
        
        return await repository.get_all(stmt)
    
    
    async def update_user(self, session: AsyncSession, user: User, **kw):
        repository = UserRepository.from_session(session)
        await repository.update(
                obj=user,
                update_dict=kw,
                flush=True
            )
    
    async def get_from_tg_id(
        self, session: AsyncSession, 
        tg_id: int,
    ) -> User | None:

        options: Options = []

        
        repository = UserRepository.from_session(session)

        stmt = repository.get_base_stmt().where(User.id == tg_id).options(*options)
  
        return await repository.get_one_or_none(stmt)

    async def get_or_create_by_init_data(
        self, session: AsyncSession, init_data: InitData
    ) -> User:
        i_user = init_data.user
        if i_user is None:
            raise BadRequest("Init data user is None")

        repository = UserRepository.from_session(session)

        # Сначала пытаемся найти существующего пользователя
        user = await repository.get_by_id(id=i_user.id)

        if user is None:
            try:
                # Пытаемся создать пользователя
                user = await repository.create(
                    obj=User(
                        id=i_user.id,
                        first_name=i_user.first_name,
                        last_name=i_user.last_name,
                        username=i_user.username,
                        is_premium=i_user.is_premium,
                        avatar=i_user.photo_url,
                    ),
                    flush=True
                )
            except IntegrityError:
                await session.rollback()
                user = await repository.get_by_id(id=i_user.id)
                
                if user is None:
                    raise BadRequest("Could not create or find user")

        return user
    

    async def get_or_create_by_tg(
        self, session: AsyncSession, tg_user: TGUser
    ) -> User:
        repository = UserRepository.from_session(session)

        # ИСПРАВЛЕНО: ищем по tg_user_id, а не по id
        user = await repository.get_by_tg_id(tg_user.id)

        if user is None:
            try:
                print(tg_user.id, tg_user.first_name, tg_user.last_name, tg_user.username)
                
                user = await repository.create(
                    obj=User(
                        tg_user_id=tg_user.id,  # Это поле, не primary key!
                        first_name=tg_user.first_name,
                        last_name=tg_user.last_name,
                        username=tg_user.username,
                    ),
                    flush=True,
                )

                print(f"Created user: id={user.id}, tg_user_id={user.tg_user_id}")
            except IntegrityError:
                await session.rollback()
                # После rollback снова ищем по tg_user_id
                user = await repository.get_by_tg_id(tg_user.id)
                print(f"After rollback: {user}")
                
                if user is None:
                    raise BadRequest("Could not create or find user")

        return user
    
    async def resolve_from_tg_user(self, session: AsyncSession, tg_user: TGUser) -> User:
        if tg_user.is_bot:
            raise ValueError("Telegram user is bot.")

        repository = self.get_repository(session)
        
        # ИСПРАВЛЕНО: ищем по tg_user_id
        user = await repository.get_by_tg_id(tg_user.id)

        if user is None:
            user = await repository.create(
                User(
                    tg_user_id=tg_user.id,
                    first_name=tg_user.first_name,
                    last_name=tg_user.last_name,
                    username=tg_user.username,
                )
            )

        return user
    


    """    ADMIN METHODS    """

    async def get_users_count(self, session: AsyncSession):
        repository = UserRepository.from_session(session)
        return await repository.count_base(repository.get_count_stmt_base())

    
    def get_repository(self, session: AsyncSession):
        return UserRepository(session)


user_service = UserService()