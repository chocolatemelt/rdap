import Koa from 'koa';

const app = new Koa();

app.use(async ctx => { ctx.body = 'hi' });
app.listen(3030);
