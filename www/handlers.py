#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

import markdown2

from aiohttp import web

from coroweb import get, post

from models import Equipment,User, Comment, Blog, next_id, Loan_records

from apis import Page, APIError, APIValueError

from config import configs

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)

def user2cookie(user, max_age):
    '''
    Generate cookie str by user.
    '''
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

async def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
    '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

@get('/')
async def index(*, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    page = Page(num)
    if num == 0:
        blogs = []
    else:
        blogs = await Blog.findAll(orderBy='created_at desc', limit=(page.offset,page.limit))

    return {
        
            '__template__': 'blogs.html',
            'page': page,
            'blogs': blogs
    }

@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }

@post('/api/authenticate')
async def authenticate(*, email, passwd):

    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    users = await User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    logging.info('api authenticate')
    user = users[0]
    # check passwd:
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out.')
    return r

@get('/manage/equipments')
def manage_equipments(*, page='1', search_info=''):
    return {
        '__template__': 'manage_equipments.html',
        'page_index': get_page_index(page),
	'search_info': search_info
    }

@get('/manage/equipmentsOnLoan')
def manage_equipmentsOnLoan(*, page='1'):
    return {
        '__template__': 'manage_equipmentsOnLoan.html',
        'page_index': get_page_index(page)
    }



@get('/user/equipments')
def user_equipments(*, page='1', search_info=''):
    return {
        '__template__': 'user_equipments.html',
        'page_index': get_page_index(page),
	'search_info': search_info
    }

@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }

@get('/manage/equipments/create')
def manage_create_equipment():
    return {
        '__template__': 'manage_equipment_edit.html',
        'id': '',
        'action': '/api/equipments'
    }

@get('/manage/equipments/edit')
def manage_edit_equipment(*, id):
    return {
        '__template__': 'manage_equipment_edit.html',
        'id': id,
        'action': '/api/equipments/%s' % id
    }



@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }

@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
    return {
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/%s' % id
    }

@get('/manage/users')
def manage_users(*, page='1'):
    return {
        '__template__': 'manage_users.html',
        'page_index': get_page_index(page)
    }

@get('/user/users')
def user_users(*, page='1'):
    return {
        '__template__': 'user_users.html',
        'page_index': get_page_index(page)
    }



@get('/manage/comments')
def manage_comments(*, page='1'):
    return {
        '__template__': 'manage_comments.html',
        'page_index': get_page_index(page)
    }

@get('/manage/records')
def manage_records(*,page='1'):
    return {
        '__template__': 'manage_records.html',
        'page_index': get_page_index(page)
    }
    
@get('/user/records')
def user_records(*,page='1'):
    return {
        '__template__': 'user_records.html',
        'page_index': get_page_index(page)
    }
 

@get('/blog/{id}')
async def get_blog(id):
    blog = await Blog.find(id)
    comments = await Comment.findAll('blog_id=?',[id], orderBy='created_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }

@get('/api/comments')
async def api_comments(*, page='1'):
    page_index = get_page_index(page)
    num = await Comment.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, comments=())
    comments = await Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, comments=comments)

@get('/api/records')
async def api_records(*, page='1'):
    page_index = get_page_index(page)
    num = await Loan_records.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, records=())
    records = await Loan_records.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, records=records )

@get('/api/user_records')
async def api_user_records(request, *, page='1'):
    user=request.__user__ 
    page_index = get_page_index(page)
    num = await Loan_records.findNumber('count(id)',where='`user_id`=\'%s\'' % user.id)
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, records=())
    records = await Loan_records.findAll(where='`user_id`=\'%s\'' % user.id, orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, records=records )


@post('/api/comments/{id}/delete')
async def api_delete_comments(id,request):
    check_admin(request)
    c = await Comment.find(id)
    if c is None:
       raise APIResourceNotFoundError('Comment')
    await c.remove()
    return dict(id=id)

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@get('/api/users')
async def api_get_users(*, page='1'):
    page_index = get_page_index(page)
    num = await User.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dic(page=p, users=())
    users = await User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    for u in users:
        u.passwd = '******'
    return dict(page=p, users=users)

@post('/api/users')
async def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='https://www.funnypica.com/wp-content/uploads/2015/05/TOP-50-Beautiful-Girls-Girl-25-of-50.jpg')
    await user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@get('/api/equipments')
async def api_equipments(request, *, page='1', search_info=''):
    user=request.__user__ 
    page_index = get_page_index(page)
    search_msg = 'CONCAT(id, name, model, asset_number, acessories, warehouse, user_id, user_name, user_image, borrow_time, time_limit, scrapped, created_at) like \'%%%%%s%%%%\'' % search_info
    logging.info('api_equipment ----------------- search_msg='+search_msg)
    num = await Equipment.findNumber('count(id)',where=search_msg)
    logging.info('api_equipment ----------------- the num of search result=%s' % num)
    p = Page(num, page_index)
    if num == 0:
        return dict(user=user, page=p, equipments=())
    equipments = await Equipment.findAll(where=search_msg, orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(user=user ,page=p, equipments=equipments)


@get('/api/equipmentsOnLoan')
async def api_equipmentsOnLoan(request, *, page='1'):
    user=request.__user__ 
    page_index = get_page_index(page)
    num = await Equipment.findNumber('count(id)',where='`user_id`!=\'\'')
    p = Page(num, page_index)
    if num == 0:
        return dict(user=user, page=p, equipments=())
    equipments = await Equipment.findAll(where='`user_id`!=\'\'', orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(user=user ,page=p, equipments=equipments)


@get('/api/blogs')
async def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)




@post('/api/blogs')
async def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
    await blog.save()
    return blog

@post('/api/equipments')
async def api_create_equipment(request, *, name, model, asset_number, acessories, warehouse, scrapped):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not model or not model.strip():
        raise APIValueError('model', 'model cannot be empty.')
    if not asset_number or not asset_number.strip():
        raise APIValueError('asset_number', 'asset_number cannot be empty.')
    equipment = Equipment(name=name.strip(), model=model.strip(), asset_number=asset_number.strip(), acessories=acessories.strip(), warehouse=warehouse.strip(), scrapped=scrapped.strip(), user_id='', user_name='', user_image='')
    await equipment.save()
    return equipment


@get('/api/equipments/{id}')
async def api_get_equipment(*, id):
    equipment = await Equipment.find(id)
    return equipment


@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)
    return blog

@post('/api/blogs/{id}/comments')
async def api_create_comment(id, request, *, content):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first.')
    if not content or not content.strip():
        raise APIValueError('content')
    blog = await Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
    await comment.save()
    return comment

@post('/api/equipments/{id}')
async def api_update_equipment(id, request, *, name, model, asset_number, acessories, warehouse, scrapped): 
    check_admin(request)
    equipment = await Equipment.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not model or not model.strip():
        raise APIValueError('model', 'model cannot be empty.')
    if not asset_number or not asset_number.strip():
        raise APIValueError('asset_number', 'asset_number cannot be empty.')
    equipment.name = name.strip()
    equipment.model = model.strip()
    equipment.asset_number = asset_number.strip()
    equipment.acessories = acessories.strip()
    equipment.warehouse = warehouse.strip()
    equipment.scrapped = scrapped.strip()
    await equipment.update()
    return equipment



@post('/api/blogs/{id}')
async def api_update_blog(id, request, *, name, summary, content):
    check_admin(request)
    blog = await Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    await blog.update()
    return blog

@post('/api/equipments/{id}/loanApproval')
async def api_laonApproval_equipment(id, *, request):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first.')
    equipment = await Equipment.find(id)
    if equipment is None:
        raise APIResourceNotFoundError('Equipment')
    Loan_record = Loan_records(equipment_id=equipment.id, equipment_name=equipment.name, equipment_model = equipment.model, acessories = equipment.acessories, user_id=equipment.user_id, user_name=equipment.user_name, user_image=equipment.user_image, action = '借出')
    await Loan_record.save()
    equipment.warehouse = '借出'
    await equipment.update()
    return Loan_record


@post('/api/equipments/{id}/loanRefuse')
async def api_laonRefuse_equipment(id, *, request):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first.')
    equipment = await Equipment.find(id)
    if equipment is None:
        raise APIResourceNotFoundError('Equipment')
    equipment.warehouse = '入库'
    equipment.user_id = ''
    equipment.user_name = ''
    equipment.user_image = ''
    equipment.borrow_time = time.time()
    await equipment.update()
    return equipment


@post('/api/equipments/{id}/borrowRequest')
async def api_borrowRequest_equipment(id, *, request):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first.')
    equipment = await Equipment.find(id)
    if equipment is None:
        raise APIResourceNotFoundError('Equipment')
    equipment.warehouse = '申请借出'
    equipment.user_id = user.id.strip()
    equipment.user_name = user.name.strip()
    equipment.user_image = user.image.strip()
    equipment.borrow_time = time.time()
    await equipment.update()
    return equipment



@post('/api/equipments/{id}/return')
async def api_return_equipment(id, *, request):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first.')
    equipment = await Equipment.find(id)
    if equipment is None:
        raise APIResourceNotFoundError('Equipment')
    Loan_record = Loan_records(equipment_id=equipment.id, equipment_name=equipment.name, equipment_model = equipment.model, acessories = equipment.acessories, user_id=equipment.user_id, user_name=equipment.user_name, user_image=equipment.user_image, action = '归还')
    await Loan_record.save()
    equipment.warehouse = '入库'
    equipment.user_id = ''
    equipment.user_name = ''
    equipment.user_image = ''
    equipment.borrow_time = time.time()
    await equipment.update()
    return Loan_record




@post('/api/equipments/{id}/delete')
async def api_delete_equipment(request, *, id):
    check_admin(request)
    equipment = await Equipment.find(id)
    await equipment.remove()
    return dict(id=id)


@post('/api/blogs/{id}/delete')
async def api_delete_blog(request, *, id):
    check_admin(request)
    blog = await Blog.find(id)
    await blog.remove()
    return dict(id=id)


#@get('/api/users/')
#async def api_get_users():
#    users =await User.findAll(orderBy='created_at desc')
#    for u in users:
#        u.passwd = '******'
#    return dict(users=users)


#@ get('/')
#async def index(request):
#    users = await User.findAll()
#    return {
#        
#            '__template__': 'test.html',
#            'users': users
#    }
