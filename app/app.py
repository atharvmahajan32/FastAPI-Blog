import os
from dotenv import load_dotenv
import uuid
import datetime
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Form, Depends
from fastapi.security import APIKeyHeader
from app.db import Post, Reason, create_db_and_tables, get_async_session
from app.schemas import PostCreate, PostUpdate, ReasonCreate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from contextlib import asynccontextmanager
from mangum import Mangum

load_dotenv()

# Allow Swagger UI to set the Authorization header
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

@asynccontextmanager 
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    app.state.admin_tokens = {}
    yield
    
app = FastAPI(lifespan=lifespan)
handler = Mangum(app)

ENV = os.environ.get('ENV', 'development').lower()

PRODUCTION_ORIGINS = [
    "https://blog.athrv.me",
    "https://react-blog-ivory-seven.vercel.app"
]

DEVELOPMENT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

origins = PRODUCTION_ORIGINS if ENV == 'production' else DEVELOPMENT_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/where_to')
async def where_to(
    name: str = Form(''),
    why: str = Form(''),
    session: AsyncSession = Depends(get_async_session)
):
    
    payload = ReasonCreate(name=name, why=why)

    if payload.name == os.environ.get('ADMIN') and payload.why == os.environ.get('KEY'):
        token = uuid.uuid4().hex
        expiry = datetime.datetime.now() + datetime.timedelta(hours=2)
        app.state.admin_tokens[token] = expiry
        return {'admin': True, 'token': token}
    else:
        reason = Reason(name=payload.name, why=payload.why)
        session.add(reason)
        await session.commit()
        await session.refresh(reason)
        return {'admin': False, 'name': reason.name, 'why': reason.why}


def _is_token_valid(token: str) -> bool:
    """Check token in app.state and validate expiry."""
    expiry = app.state.admin_tokens.get(token)
    if not expiry:
        return False
    if expiry < datetime.datetime.now():
        try:
            del app.state.admin_tokens[token]
        except KeyError:
            pass
        return False
    return True


async def require_admin(api_key: str | None = Depends(api_key_header)):
    """Dependency to require a valid admin token in Authorization header.

    Expects: Authorization: Bearer <token>
    """
    if not api_key:
        raise HTTPException(status_code=401, detail='Missing Authorization header')
    parts = api_key.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        raise HTTPException(status_code=401, detail='Invalid Authorization header')
    token = parts[1]
    if not _is_token_valid(token):
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    return True

@app.get('/get_reasons')
async def get_reasons(session: AsyncSession = Depends(get_async_session)):
    results = await session.execute(select(Reason).order_by(Reason.created_at.desc()))
    reasons = [row[0] for row in results.all()]
    reasons_data = []
    for reason in reasons:
        reasons_data.append(
            {
                'id': str(reason.id),
                'name': reason.name,
                'why': reason.why,
                'created_at': reason.created_at.isoformat()
            }
        )
        
    return {"posts": reasons_data}

@app.delete('/reasons/{reason_id}')
async def delete_reason(
    reason_id: str,
    session: AsyncSession = Depends(get_async_session),
    _admin: bool = Depends(require_admin)
):
    try:
        reason_uuid = uuid.UUID(reason_id)
        result = await session.execute(select(Reason).where(Reason.id == reason_uuid))
        reason = result.scalars().first()
        
        if not reason:
            raise HTTPException(status_code=404, detail='Reason not found')
        
        await session.delete(reason)
        await session.commit()
        
        return {'success': True, 'message': 'Reason deleted successfully'}
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid reason ID format')

@app.post('/upload')
async def upload(
    title: str = Form(''),
    content: str = Form(''),
    session: AsyncSession = Depends(get_async_session),
    _admin: bool = Depends(require_admin)
):
    
    payload = PostCreate(title=title, content=content)
    post = Post(title=payload.title, content=payload.content)
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post

@app.get('/get')
async def get(
    session: AsyncSession = Depends(get_async_session)
):
    results = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in results.all()]
    posts_data = []
    for post in posts:
        posts_data.append(
            {
                'id': str(post.id),
                'title': post.title,
                'content': post.content,
                'created_at': post.created_at.isoformat()
            }
        )
        
    return {"posts": posts_data}

@app.get('/get/{post_id}')
async def get_post_by_id(
    post_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    try:
        post_uuid = uuid.UUID(post_id)
        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()
        
        if not post:
            raise HTTPException(status_code=404, detail='Post not found')
        
        return {
            'id': str(post.id),
            'title': post.title,
            'content': post.content,
            'created_at': post.created_at.isoformat()
        }
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid post ID format')

@app.put('/update/{post_id}')
async def update(
    post_id: str,
    title: str = Form(None),
    content: str = Form(None),
    session: AsyncSession = Depends(get_async_session),
    _admin: bool = Depends(require_admin)
):
    try:
        post_uuid = uuid.UUID(post_id)
        
        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()
        
        if not post:
            raise HTTPException(status_code=404, detail='Post not found')
        
        update_payload = PostUpdate(title=title, content=content)
        if update_payload.title is not None:
            post.title = update_payload.title # type: ignore
        if update_payload.content is not None:
            post.content = update_payload.content # type: ignore
        
        session.add(post)
        await session.commit()
        await session.refresh(post)
        
        return {
            'id': str(post.id),
            'title': post.title,
            'content': post.content,
            'created_at': post.created_at.isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/posts/{post_id}')
async def delete_post(post_id: str, session: AsyncSession = Depends(get_async_session), _admin: bool = Depends(require_admin)):
    try:
        post_uuid = uuid.UUID(post_id)
        
        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()
        
        if not post:
            raise HTTPException(status_code=404, detail='Post not found')
        await session.delete(post)
        await session.commit()
        
        return {'Success': True, 'Message': 'Post deleted successfully'}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

